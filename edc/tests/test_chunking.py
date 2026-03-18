from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List

from edc.preprocessing.chunking_v1 import chunk_document as chunk_document_v1
from edc.preprocessing.chunking_v2 import chunk_document as chunk_document_v2


def summarize_chunks(name: str, chunks: List[Dict], example_count: int, max_preview_chars: int) -> None:
    print(f"\n=== {name} ===")

    if not chunks:
        print("Anzahl Chunks: 0")
        print("Max Groesse Chunk: 0")
        print("Min Groesse Chunk: 0")
        print("Beispiele: keine")
        return

    lengths = [len(chunk.get("text_for_edc", "")) for chunk in chunks]

    print(f"Anzahl Chunks: {len(chunks)}")
    print(f"Max Groesse Chunk: {max(lengths)}")
    print(f"Min Groesse Chunk: {min(lengths)}")

    print("Beispiele:")
    for idx, chunk in enumerate(chunks[:example_count], start=1):
        text = chunk.get("text_for_edc", "").replace("\n", " ").strip()
        if len(text) > max_preview_chars:
            text = text[: max_preview_chars - 3] + "..."
        print(
            f"  {idx}. chunk_id={chunk.get('chunk_id')} | "
            f"type={chunk.get('chunk_type')} | "
            f"size={len(chunk.get('text_for_edc', ''))}\n"
            f"     {text}"
        )


def write_chunks_to_txt(output_file: Path, chunks: List[Dict]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file_obj:
        for idx, chunk in enumerate(chunks, start=1):
            file_obj.write(f"=== CHUNK {idx} ===\n")
            file_obj.write(f"doc_id: {chunk.get('doc_id', '')}\n")
            file_obj.write(f"chunk_id: {chunk.get('chunk_id', '')}\n")
            file_obj.write(f"section_id: {chunk.get('section_id', '')}\n")
            file_obj.write(f"section_title: {chunk.get('section_title', '')}\n")
            file_obj.write(f"chunk_type: {chunk.get('chunk_type', '')}\n")
            file_obj.write(f"source_span: {chunk.get('source_span', None)}\n")
            file_obj.write(f"meta: {chunk.get('meta', {})}\n")
            file_obj.write("text_for_edc:\n")
            file_obj.write(chunk.get("text_for_edc", ""))
            file_obj.write("\n\n")


def main() -> None:
    parser = ArgumentParser(description="Run v1 and v2 chunkers on one TXT file and print summary stats.")
    parser.add_argument("--input_text_file_path", required=True, help="Path to input TXT file.")
    parser.add_argument("--doc_id", default=None, help="Optional document id override.")

    # v1 settings
    parser.add_argument("--v1_mode", choices=["sentence", "char"], default="sentence")
    parser.add_argument("--v1_window_sentences", type=int, default=4)
    parser.add_argument("--v1_overlap_sentences", type=int, default=1)
    parser.add_argument("--v1_window_chars", type=int, default=1800)
    parser.add_argument("--v1_overlap_chars", type=int, default=300)

    # v2 settings
    parser.add_argument("--v2_max_chunk_chars", type=int, default=2200)
    parser.add_argument("--v2_bullet_group_size", type=int, default=6)
    parser.add_argument("--v2_prose_window_sentences", type=int, default=4)
    parser.add_argument("--v2_prose_overlap_sentences", type=int, default=1)
    parser.add_argument("--v2_table_rows_per_chunk", type=int, default=25)

    # output formatting
    parser.add_argument("--example_count", type=int, default=3, help="How many sample chunks to print per chunker.")
    parser.add_argument("--max_preview_chars", type=int, default=220, help="Max preview length per sample chunk.")
    parser.add_argument(
        "--output_dir",
        default="./output/chunking_debug",
        help="Directory to write full chunk dumps for v1 and v2.",
    )
    parser.add_argument(
        "--output_prefix",
        default=None,
        help="Optional output filename prefix. Defaults to input file stem.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_text_file_path)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input_text_file_path}")

    text = input_path.read_text(encoding="utf-8")
    doc_id = args.doc_id if args.doc_id else input_path.stem

    chunks_v1 = chunk_document_v1(
        doc_id=doc_id,
        text=text,
        mode=args.v1_mode,
        window_sentences=args.v1_window_sentences,
        overlap_sentences=args.v1_overlap_sentences,
        window_chars=args.v1_window_chars,
        overlap_chars=args.v1_overlap_chars,
    )

    chunks_v2 = chunk_document_v2(
        doc_id=doc_id,
        text=text,
        max_chunk_chars=args.v2_max_chunk_chars,
        bullet_group_size=args.v2_bullet_group_size,
        prose_window_sentences=args.v2_prose_window_sentences,
        prose_overlap_sentences=args.v2_prose_overlap_sentences,
        table_rows_per_chunk=args.v2_table_rows_per_chunk,
    )

    print(f"Input file: {input_path}")
    print(f"doc_id: {doc_id}")

    summarize_chunks("Chunking V1 (Baseline Fixed-Window)", chunks_v1, args.example_count, args.max_preview_chars)
    summarize_chunks("Chunking V2 (Adaptive Section)", chunks_v2, args.example_count, args.max_preview_chars)

    output_dir = Path(args.output_dir)
    output_prefix = args.output_prefix if args.output_prefix else input_path.stem

    v1_output_file = output_dir / f"{output_prefix}_chunks_v1.txt"
    v2_output_file = output_dir / f"{output_prefix}_chunks_v2.txt"

    write_chunks_to_txt(v1_output_file, chunks_v1)
    write_chunks_to_txt(v2_output_file, chunks_v2)

    print("\nChunk dumps geschrieben:")
    print(f"- {v1_output_file}")
    print(f"- {v2_output_file}")


if __name__ == "__main__":
    main()
