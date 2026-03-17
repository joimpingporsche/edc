import pdfplumber
import json
import re
import argparse
from pathlib import Path


def clean_cell(cell):
    """Normalize whitespace and strip empty content."""
    if cell is None:
        return ""
    cell = str(cell)
    cell = cell.replace("\n", " ")
    cell = re.sub(r"\s+", " ", cell).strip()
    return cell


def normalize_headers(headers):
    """
    Normalize table headers:
    - lowercase
    - replace spaces with underscores
    - fallback names if headers are missing
    """
    normalized = []
    used = set()

    for idx, h in enumerate(headers):
        h = clean_cell(h).lower()
        if not h:
            h = f"column_{idx+1}"
        h = re.sub(r"[^a-z0-9_ ]", "", h)
        h = h.replace(" ", "_")

        base = h
        counter = 2
        while h in used:
            h = f"{base}_{counter}"
            counter += 1

        used.add(h)
        normalized.append(h)

    return normalized


def fill_down_merged_cells(rows):
    """
    Fill empty cells with previous row values.
    Useful when PDFs visually merge cells across multiple rows.
    """
    previous = None
    output = []

    for row in rows:
        if previous is None:
            previous = row.copy()
            output.append(row)
            continue

        filled = {}
        for key, value in row.items():
            if value == "":
                filled[key] = previous.get(key, "")
            else:
                filled[key] = value

        previous = filled.copy()
        output.append(filled)

    return output


def process_table(table_data, page_number, table_number):
    """
    Convert one extracted table into structured rows.
    """
    cleaned = [[clean_cell(cell) for cell in row] for row in table_data if row]
    cleaned = [row for row in cleaned if any(cell for cell in row)]

    if len(cleaned) < 2:
        return []

    headers = normalize_headers(cleaned[0])
    data_rows = cleaned[1:]

    normalized_rows = []
    for row in data_rows:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[:len(headers)]

        obj = dict(zip(headers, row))
        normalized_rows.append(obj)

    normalized_rows = fill_down_merged_cells(normalized_rows)

    enriched = []
    for idx, row in enumerate(normalized_rows, start=1):
        item = {
            "_page": page_number,
            "_table": table_number,
            "_row": idx,
            **row
        }
        enriched.append(item)

    return enriched


def word_center_in_bbox(word, bbox, margin=1):
    """
    Check whether the center of a word lies inside a bounding box.
    bbox format: (x0, top, x1, bottom)
    """
    x0, top, x1, bottom = bbox
    cx = (word["x0"] + word["x1"]) / 2
    cy = (word["top"] + word["bottom"]) / 2

    return (
        (x0 - margin) <= cx <= (x1 + margin)
        and (top - margin) <= cy <= (bottom + margin)
    )


def extract_non_table_text(page, table_bboxes, x_tolerance=3, y_tolerance=3):
    """
    Extract only text that is outside detected table regions.
    """
    words = page.extract_words(
        x_tolerance=x_tolerance,
        y_tolerance=y_tolerance,
        keep_blank_chars=False,
        use_text_flow=True
    )

    # Filter words that are NOT inside any table bbox
    non_table_words = []
    for word in words:
        inside_table = any(word_center_in_bbox(word, bbox) for bbox in table_bboxes)
        if not inside_table:
            non_table_words.append(word)

    if not non_table_words:
        return ""

    # Sort words top-to-bottom, left-to-right
    non_table_words = sorted(non_table_words, key=lambda w: (round(w["top"], 1), w["x0"]))

    # Reconstruct lines
    lines = []
    current_line = []
    current_top = None

    for word in non_table_words:
        if current_top is None:
            current_top = word["top"]
            current_line = [word]
            continue

        if abs(word["top"] - current_top) <= y_tolerance:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
            current_top = word["top"]

    if current_line:
        lines.append(current_line)

    # Convert each line to text
    line_texts = []
    for line in lines:
        line = sorted(line, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            line_texts.append(text)

    # Light cleanup
    result = "\n".join(line_texts)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result


def extract_non_table_lines(page, table_bboxes, x_tolerance=3, y_tolerance=3):
    """
    Extract text lines outside tables and keep their vertical position (top),
    so they can later be merged with table JSON in reading order.
    """
    words = page.extract_words(
        x_tolerance=x_tolerance,
        y_tolerance=y_tolerance,
        keep_blank_chars=False,
        use_text_flow=True
    )

    # keep only words outside all table bounding boxes
    non_table_words = []
    for word in words:
        inside_table = any(word_center_in_bbox(word, bbox) for bbox in table_bboxes)
        if not inside_table:
            non_table_words.append(word)

    if not non_table_words:
        return []

    # sort top-to-bottom, left-to-right
    non_table_words = sorted(
        non_table_words,
        key=lambda w: (round(w["top"], 1), w["x0"])
    )

    # group into lines
    lines = []
    current_line = []
    current_top = None

    for word in non_table_words:
        if current_top is None:
            current_top = word["top"]
            current_line = [word]
            continue

        if abs(word["top"] - current_top) <= y_tolerance:
            current_line.append(word)
        else:
            line = sorted(current_line, key=lambda w: w["x0"])
            text = " ".join(w["text"] for w in line)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                lines.append({
                    "top": current_top,
                    "text": text
                })

            current_line = [word]
            current_top = word["top"]

    # last line
    if current_line:
        line = sorted(current_line, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            lines.append({
                "top": current_top,
                "text": text
            })

    return lines


def render_table_json_block(rows):
    """
    Render one table as a JSON block for the combined TXT output.
    Metadata fields (_page, _table, _row) are removed there,
    because the combined file should focus on readable content.
    """
    content_rows = []
    for row in rows:
        content_rows.append({
            k: v for k, v in row.items()
            if not k.startswith("_")
        })

    json_lines = [json.dumps(row, ensure_ascii=False) for row in content_rows]
    json_block = "[\n" + ",\n".join(json_lines) + "\n]"

    return f"[TABLE_JSON_START]\n{json_block}\n[TABLE_JSON_END]"


def find_and_extract_tables(page):
    """
    Detect tables on a page and return both:
    - table objects (with bbox)
    - extracted raw table data
    """
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_tolerance": 5,
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
    }

    table_objects = page.find_tables(table_settings=table_settings)
    return table_objects


def main(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    plain_text_pages = []
    combined_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            table_objects = find_and_extract_tables(page)
            table_bboxes = [t.bbox for t in table_objects]

            page_elements = []

            # Extract and structure tables
            for table_idx, table_obj in enumerate(table_objects, start=1):
                table_data = table_obj.extract()
                rows = process_table(table_data, page_idx, table_idx)
                all_rows.extend(rows)

                if rows:
                    page_elements.append({
                        "kind": "table",
                        "top": table_obj.bbox[1],
                        "text": render_table_json_block(rows)
                    })

            # Extract only text outside tables (for plain_text.txt)
            non_table_text = extract_non_table_text(page, table_bboxes)
            if non_table_text:
                plain_text_pages.append({
                    "page": page_idx,
                    "text": non_table_text
                })

            # Extract line-based text outside tables for combined output
            text_lines = extract_non_table_lines(page, table_bboxes)
            for line in text_lines:
                page_elements.append({
                    "kind": "text",
                    "top": line["top"],
                    "text": line["text"]
                })

            # Sort page elements by vertical position
            page_elements = sorted(page_elements, key=lambda e: e["top"])

            combined_pages.append({
                "page": page_idx,
                "elements": page_elements
            })

    # 1) Save plain text outside tables only
    plain_text_file = output_dir / f"{pdf_path.stem}_plain_text.txt"
    with open(plain_text_file, "w", encoding="utf-8") as f:
        for page in plain_text_pages:
            f.write(f"=== PAGE {page['page']} ===\n")
            f.write(page["text"])
            f.write("\n\n")

    # 2) Save structured table rows only
    jsonl_file = output_dir / f"{pdf_path.stem}_tables.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 3) Save combined text + table JSON in reading order
    combined_file = output_dir / f"{pdf_path.stem}_combined.txt"
    with open(combined_file, "w", encoding="utf-8") as f:
        for page in combined_pages:
           # f.write(f"=== PAGE {page['page']} ===\n")
            for element in page["elements"]:
                f.write(element["text"])
                f.write("\n")

    print("Done.\n")
    print(f"Plain text (without tables): {plain_text_file}")
    print(f"Structured tables JSONL:     {jsonl_file}")
    print(f"Combined text + table JSON:  {combined_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract plain text outside tables, structured tables, and a combined text+table JSON file from a PDF."
    )
    parser.add_argument("pdf_path", help="Path to input PDF")
    parser.add_argument(
        "--output_dir",
        default="output_pdf_extraction",
        help="Directory for output files"
    )
    args = parser.parse_args()

    main(args.pdf_path, args.output_dir)
