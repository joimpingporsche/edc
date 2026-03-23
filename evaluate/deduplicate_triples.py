import argparse
import ast
from pathlib import Path
from typing import List, Tuple


Triple = Tuple[str, str, str]


def parse_line(line: str, line_no: int) -> List[Triple]:
    try:
        parsed = ast.literal_eval(line)
    except Exception as exc:
        raise ValueError(f"Line {line_no}: cannot parse as Python literal: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"Line {line_no}: expected a list, got {type(parsed).__name__}")

    triples: List[Triple] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise ValueError(f"Line {line_no}, item {idx}: expected triple with length 3")
        triples.append((str(item[0]), str(item[1]), str(item[2])))
    return triples


def dedup_keep_order(triples: List[Triple], global_seen=None) -> Tuple[List[Triple], int]:
    if global_seen is None:
        global_seen = set()
    result: List[Triple] = []
    removed = 0
    for triple in triples:
        if triple in global_seen:
            removed += 1
            continue
        global_seen.add(triple)
        result.append(triple)
    return result, removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove duplicate triples from a file where each line is a Python list of triples."
    )
    parser.add_argument("--input", required=True, help="Input file path (e.g., canon_kg.txt)")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument(
        "--scope",
        choices=["line", "global"],
        default="global",
        help="Dedup scope: line removes duplicates within each line; global removes duplicates across entire file",
    )
    parser.add_argument(
        "--keep_empty_lines",
        action="store_true",
        help="Keep empty lines unchanged in output",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    output_lines: List[str] = []

    total_before = 0
    total_after = 0
    total_removed = 0
    global_seen = set()

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line:
            if args.keep_empty_lines:
                output_lines.append("")
            continue

        triples = parse_line(line, line_no)
        total_before += len(triples)

        if args.scope == "global":
            deduped, removed = dedup_keep_order(triples, global_seen=global_seen)
        else:
            deduped, removed = dedup_keep_order(triples, global_seen=set())

        total_removed += removed
        total_after += len(deduped)
        output_lines.append(str([[s, p, o] for s, p, o in deduped]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")

    print("=== Triple Deduplication ===")
    print(f"input:  {input_path}")
    print(f"output: {output_path}")
    print(f"scope:  {args.scope}")
    print(f"triples_before:  {total_before}")
    print(f"triples_after:   {total_after}")
    print(f"triples_removed: {total_removed}")


if __name__ == "__main__":
    main()