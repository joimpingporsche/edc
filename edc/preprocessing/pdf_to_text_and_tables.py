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


def fix_spaced_word(value):
    """
    Fix common PDF extraction artifacts like:
    'O bjective' -> 'Objective'
    'I nitiative' -> 'Initiative'
    """
    if not isinstance(value, str):
        return value

    value = re.sub(r"\b([A-Z])\s+([a-z][a-zA-Z]+)\b", r"\1\2", value)
    return value


def clean_row_values(rows):
    """Apply cleanup to all string values in structured rows."""
    cleaned_rows = []
    for row in rows:
        cleaned = {}
        for k, v in row.items():
            if isinstance(v, str):
                cleaned[k] = fix_spaced_word(v)
            else:
                cleaned[k] = v
        cleaned_rows.append(cleaned)
    return cleaned_rows


def fill_down_merged_cells(rows, seed_row=None):
    """
    Fill empty cells with previous row values.
    If seed_row is provided, empty cells in the first row can inherit values
    from the last row of the previous page/table continuation.
    """
    previous = seed_row.copy() if seed_row else None
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
    Assumes first row is the header.
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
    normalized_rows = clean_row_values(normalized_rows)

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


def render_table_json_block(rows):
    """
    Render one table as a JSON block.
    Each row is written as a single-line JSON object.
    Metadata fields (_page, _table, _row) are removed here.
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


def group_words_to_lines(words, y_tolerance=3):
    """
    Convert word list into physical text lines.
    """
    if not words:
        return []

    words = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))

    lines = []
    current_line = []
    current_top = None

    for word in words:
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
                lines.append({"top": current_top, "text": text})

            current_line = [word]
            current_top = word["top"]

    if current_line:
        line = sorted(current_line, key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            lines.append({"top": current_top, "text": text})

    return lines


def lines_to_sentences(lines):
    """
    Merge physical PDF lines into sentence-like blocks.
    A new line is written only after '.', '!' or ':'.
    """
    if not lines:
        return []

    sentences = []
    buffer_text = ""
    buffer_top = None

    for line in lines:
        if buffer_top is None:
            buffer_top = line["top"]
            buffer_text = line["text"]
        else:
            buffer_text += " " + line["text"]

        buffer_text = re.sub(r"\s+", " ", buffer_text).strip()

        if re.search(r"[\.\!\:]$", buffer_text):
            sentences.append({
                "top": buffer_top,
                "text": buffer_text
            })
            buffer_text = ""
            buffer_top = None

    if buffer_text:
        sentences.append({
            "top": buffer_top,
            "text": re.sub(r"\s+", " ", buffer_text).strip()
        })

    return sentences


def extract_non_table_lines(page, table_bboxes, x_tolerance=3, y_tolerance=3):
    """
    Extract text lines outside tables and keep their vertical position (top).
    """
    words = page.extract_words(
        x_tolerance=x_tolerance,
        y_tolerance=y_tolerance,
        keep_blank_chars=False,
        use_text_flow=True
    )

    non_table_words = []
    for word in words:
        inside_table = any(word_center_in_bbox(word, bbox) for bbox in table_bboxes)
        if not inside_table:
            non_table_words.append(word)

    return group_words_to_lines(non_table_words, y_tolerance=y_tolerance)


def find_and_extract_tables(page):
    """
    Detect tables on a page and return table objects.
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


def find_horizontal_separators(page, min_width_ratio=0.6, max_thickness=3, merge_tolerance=5):
    """
    Detect horizontal separator lines on the page.
    Uses page.lines and thin page.rects as candidates.
    """
    separators = []
    page_width = page.width
    min_width = page_width * min_width_ratio

    # line objects
    for line in page.lines:
        x0 = line.get("x0", 0)
        x1 = line.get("x1", 0)
        top = line.get("top", 0)
        bottom = line.get("bottom", top)
        width = abs(x1 - x0)
        height = abs(bottom - top)

        if width >= min_width and height <= max_thickness:
            separators.append((top + bottom) / 2)

    # very thin rectangles
    for rect in page.rects:
        x0 = rect.get("x0", 0)
        x1 = rect.get("x1", 0)
        top = rect.get("top", 0)
        bottom = rect.get("bottom", top)
        width = abs(x1 - x0)
        height = abs(bottom - top)

        if width >= min_width and height <= max_thickness:
            separators.append((top + bottom) / 2)

    separators = sorted(separators)

    merged = []
    for y in separators:
        if not merged or abs(y - merged[-1]) > merge_tolerance:
            merged.append(y)

    return merged


def extract_band_words(page, band_top, band_bottom, table_bboxes):
    """
    Extract words inside a vertical band, excluding tables.
    """
    words = page.extract_words(
        x_tolerance=3,
        y_tolerance=3,
        keep_blank_chars=False,
        use_text_flow=True
    )

    result = []
    for word in words:
        cy = (word["top"] + word["bottom"]) / 2
        inside_band = band_top <= cy <= band_bottom
        inside_table = any(word_center_in_bbox(word, bbox) for bbox in table_bboxes)

        if inside_band and not inside_table:
            result.append(word)

    return result


def extract_table_anchors_in_band(table_anchors, band_top, band_bottom):
    """
    Return table anchors that start inside a vertical band.
    """
    return [
        anchor for anchor in table_anchors
        if band_top <= anchor["top"] <= band_bottom
    ]


def looks_like_section_title(text):
    """
    Heuristic to decide whether a line looks like a section title.
    """
    text = clean_cell(text)

    if not text:
        return False

    # headings are usually short and not sentence-ending
    if len(text) > 120:
        return False

    if text.endswith("."):
        return False

    # bullets are not titles
    if text.startswith("-") or text.startswith("•") or text.startswith("o "):
        return False

    # strong signal: title case / heading style
    words = text.split()
    if 1 <= len(words) <= 12:
        return True

    return False


def build_page_bands(page, table_bboxes):
    """
    Build vertical page bands using detected horizontal separator lines.
    If no separators are found, return one single band covering the whole page.
    """
    separators = find_horizontal_separators(page)

    if not separators:
        return [(0, page.height)]

    bounds = [0] + separators + [page.height]
    bands = []

    for i in range(len(bounds) - 1):
        top = bounds[i]
        bottom = bounds[i + 1]
        if bottom - top > 5:
            bands.append((top, bottom))

    return bands


def merge_text_elements_into_sentences(elements):
    """
    Merge consecutive text elements into sentence-like blocks.
    Flush when sentence ends or before/after a table block.
    """
    merged = []
    buffer_text = None
    buffer_top = None

    for element in elements:
        if element["kind"] == "table":
            if buffer_text:
                merged.append({
                    "kind": "text",
                    "top": buffer_top,
                    "text": re.sub(r"\s+", " ", buffer_text).strip()
                })
                buffer_text = None
                buffer_top = None

            merged.append(element)
            continue

        if buffer_text is None:
            buffer_text = element["text"]
            buffer_top = element["top"]
        else:
            buffer_text += " " + element["text"]

        buffer_text = re.sub(r"\s+", " ", buffer_text).strip()

        if re.search(r"[\.\!\:]$", buffer_text):
            merged.append({
                "kind": "text",
                "top": buffer_top,
                "text": buffer_text
            })
            buffer_text = None
            buffer_top = None

    if buffer_text:
        merged.append({
            "kind": "text",
            "top": buffer_top,
            "text": re.sub(r"\s+", " ", buffer_text).strip()
        })

    return merged


def extract_section_candidates_from_page(page, table_anchors, table_bboxes):
    """
    Split a page into candidate sections using horizontal separator lines.
    The first text line in a band is treated as a title if it looks like one.
    Tables are inserted inline as separate elements.
    """
    bands = build_page_bands(page, table_bboxes)
    section_candidates = []

    for band_top, band_bottom in bands:
        band_words = extract_band_words(page, band_top, band_bottom, table_bboxes)
        band_lines = group_words_to_lines(band_words)
        band_tables = extract_table_anchors_in_band(table_anchors, band_top, band_bottom)

        if not band_lines and not band_tables:
            continue

        # Build ordered elements inside this band
        elements = []

        for line in band_lines:
            elements.append({
                "kind": "text",
                "top": line["top"],
                "text": line["text"]
            })

        for table_anchor in band_tables:
            elements.append({
                "kind": "table",
                "top": table_anchor["top"],
                "logical_table_id": table_anchor["logical_table_id"]
            })

        elements = sorted(elements, key=lambda e: e["top"])

        title = None
        body_elements = elements

        # First text line can become title
        first_text_idx = None
        for idx, el in enumerate(elements):
            if el["kind"] == "text":
                first_text_idx = idx
                break

        if first_text_idx is not None:
            first_text = elements[first_text_idx]["text"]
            if looks_like_section_title(first_text):
                title = first_text
                body_elements = elements[:first_text_idx] + elements[first_text_idx + 1:]

        section_candidates.append({
            "band_top": band_top,
            "band_bottom": band_bottom,
            "title": title,
            "elements": body_elements
        })

    return section_candidates


def finalize_section_content(elements, logical_tables):
    """
    Convert section body elements into final text blocks:
    - merge text into sentences
    - insert table JSON blocks inline
    """
    resolved_elements = []

    for el in elements:
        if el["kind"] == "table":
            logical_table_id = el["logical_table_id"]
            rows = logical_tables.get(logical_table_id, {}).get("rows", [])
            resolved_elements.append({
                "kind": "table",
                "top": el["top"],
                "text": render_table_json_block(rows)
            })
        else:
            resolved_elements.append(el)

    resolved_elements = sorted(resolved_elements, key=lambda e: e["top"])
    resolved_elements = merge_text_elements_into_sentences(resolved_elements)

    content_parts = [el["text"] for el in resolved_elements]
    return content_parts


def render_section_block(title, pages, content_parts):
    """
    Render one section into the requested tagged format.
    Tables are already included inline inside content_parts.
    """
    lines = []
    lines.append("[SECTION_START]")
    lines.append(f"TITLE: {title if title else 'Untitled Section'}")
  #  lines.append("PAGES: " + ", ".join(str(p) for p in pages))
    lines.append("CONTENT:")
    for part in content_parts:
        lines.append(part)
    lines.append("[SECTION_END]")
    return "\n".join(lines)


def merge_section_candidates_across_pages(section_candidates_by_page, logical_tables):
    """
    Merge page-level section candidates into document-level sections.

    Rules:
    - if a candidate has a title -> start a new section
    - if a candidate has no title -> append to previous section if it exists
    - otherwise create an untitled section
    """
    final_sections = []
    current_section = None

    for page_idx, candidates in section_candidates_by_page:
        for candidate in candidates:
            title = candidate["title"]
            content_parts = finalize_section_content(candidate["elements"], logical_tables)

            # skip completely empty candidates
            if (not title) and (not content_parts):
                continue

            if title:
                if current_section:
                    final_sections.append(current_section)

                current_section = {
                    "title": title,
                    "pages": [page_idx],
                    "content_parts": content_parts.copy()
                }
            else:
                if current_section is None:
                    current_section = {
                        "title": "Untitled Section",
                        "pages": [page_idx],
                        "content_parts": content_parts.copy()
                    }
                else:
                    if page_idx not in current_section["pages"]:
                        current_section["pages"].append(page_idx)
                    current_section["content_parts"].extend(content_parts)

    if current_section:
        final_sections.append(current_section)

    return final_sections


def main(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    plain_text_pages = []

    logical_tables = {}
    next_logical_table_id = 1

    # page-wise anchors for tables (used later to insert tables into sections)
    page_table_anchors = {}

    with pdfplumber.open(pdf_path) as pdf:
        # --- PASS 1: tables + plain text ---
        for page_idx, page in enumerate(pdf.pages, start=1):
            table_objects = find_and_extract_tables(page)
            table_bboxes = [t.bbox for t in table_objects]

            page_table_anchors[page_idx] = []

            # tables
            for table_obj in table_objects:
                table_data = table_obj.extract()
                logical_table_id = next_logical_table_id
                next_logical_table_id += 1

                rows = process_table(table_data, page_idx, logical_table_id)
                if rows:
                    all_rows.extend(rows)
                    logical_tables[logical_table_id] = {
                        "rows": rows.copy(),
                        "page": page_idx,
                        "top": table_obj.bbox[1]
                    }

                    page_table_anchors[page_idx].append({
                        "top": table_obj.bbox[1],
                        "logical_table_id": logical_table_id
                    })

            # plain text outside tables
            text_lines = extract_non_table_lines(page, table_bboxes)
            sentence_lines = lines_to_sentences(text_lines)
            if sentence_lines:
                plain_text_pages.append({
                    "page": page_idx,
                    "lines": sentence_lines
                })

        # --- PASS 2: section candidates per page ---
        section_candidates_by_page = []

        for page_idx, page in enumerate(pdf.pages, start=1):
            table_objects = find_and_extract_tables(page)
            table_bboxes = [t.bbox for t in table_objects]
            table_anchors = page_table_anchors.get(page_idx, [])

            candidates = extract_section_candidates_from_page(
                page,
                table_anchors=table_anchors,
                table_bboxes=table_bboxes
            )

            section_candidates_by_page.append((page_idx, candidates))

    # Merge page-level section candidates into document-level sections
    final_sections = merge_section_candidates_across_pages(
        section_candidates_by_page,
        logical_tables
    )

    # 1) Save plain text outside tables only
    plain_text_file = output_dir / f"{pdf_path.stem}_plain_text.txt"
    with open(plain_text_file, "w", encoding="utf-8") as f:
        for page in plain_text_pages:
            f.write(f"=== PAGE {page['page']} ===\n")
            for line in page["lines"]:
                f.write(line["text"])
                f.write("\n")

    # 2) Save structured table rows only
    jsonl_file = output_dir / f"{pdf_path.stem}_tables.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 3) Save combined section-based export
    combined_file = output_dir / f"{pdf_path.stem}_combined.txt"
    with open(combined_file, "w", encoding="utf-8") as f:
        for section in final_sections:
            f.write(render_section_block(
                title=section["title"],
                pages=section["pages"],
                content_parts=section["content_parts"]
            ))
            f.write("\n")

    print("Done.\n")
    print(f"Plain text (without tables): {plain_text_file}")
    print(f"Structured tables JSONL:     {jsonl_file}")
    print(f"Combined sections export:    {combined_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Extract plain text outside tables, structured table JSONL, and a "
            "section-based combined export from a PDF. Sections are derived from "
            "horizontal separators and titles; tables are inserted inline as JSON."
        )
    )
    parser.add_argument("pdf_path", help="Path to input PDF")
    parser.add_argument(
        "--output_dir",
        default="output_pdf_extraction",
        help="Directory for output files"
    )
    args = parser.parse_args()

    main(args.pdf_path, args.output_dir)