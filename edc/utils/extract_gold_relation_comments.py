import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


OBJECT_PROPERTY_BLOCK_RE = re.compile(
    r"^\s*(?P<subject>\S+)\s+rdf:type\s+owl:ObjectProperty\s*;(?P<body>.*?)(?=^\s*###\s|\Z)",
    re.MULTILINE | re.DOTALL,
)

COMMENT_RE = re.compile(r'rdfs:comment\s+"(?P<comment>(?:[^"\\]|\\.)*)"\s*@en\s*[\.;]')


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_relation_name(subject_token: str) -> str:
    token = subject_token.strip()

    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1]
        if "#" in token:
            return token.rsplit("#", 1)[-1]
        return token.rsplit("/", 1)[-1]

    if ":" in token:
        return token.split(":", 1)[1]

    return token


def extract_relation_comment_map(ttl_path: Path) -> Tuple[Dict[str, str], List[str]]:
    text = ttl_path.read_text(encoding="utf-8")

    relation_to_comment: Dict[str, str] = {}
    warnings: List[str] = []

    for match in OBJECT_PROPERTY_BLOCK_RE.finditer(text):
        subject = match.group("subject")
        body = match.group("body")

        relation = _extract_relation_name(subject)
        relation = _normalize_text(relation)

        # Skip template placeholder entries like <?predicate>.
        if not relation or "?" in relation:
            continue

        # Keep only rel* names that specifically start with relTo*.
        if relation.startswith("rel") and not relation.startswith("relTo"):
            continue

        comment_match = COMMENT_RE.search(body)
        if not comment_match:
            warnings.append(f"No rdfs:comment found for relation '{relation}'.")
            continue

        comment = _normalize_text(comment_match.group("comment"))
        if not comment:
            warnings.append(f"Empty rdfs:comment for relation '{relation}'.")
            continue

        if relation in relation_to_comment and relation_to_comment[relation] != comment:
            # Keep the longest definition if duplicates differ.
            chosen = max([relation_to_comment[relation], comment], key=len)
            relation_to_comment[relation] = chosen
            warnings.append(
                f"Multiple comments found for relation '{relation}'. Kept longest definition."
            )
        else:
            relation_to_comment[relation] = comment

    relation_to_comment = dict(sorted(relation_to_comment.items(), key=lambda item: item[0]))
    return relation_to_comment, warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract relation definitions from rdfs:comment of owl:ObjectProperty entries in a TTL ontology."
    )
    parser.add_argument(
        "--input",
        default="datasets/intern/gold/leanix_ontology.ttl",
        help="Path to ontology TTL file.",
    )
    parser.add_argument(
        "--output",
        default="datasets/intern/gold/leanix_relation_definitions_from_ttl.json",
        help="Output JSON path for relation-to-definition mapping.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    relation_map, warnings = extract_relation_comment_map(input_path)

    output_payload = {
        "input_file": str(input_path),
        "relations_total": len(relation_map),
        "relation_definitions": relation_map,
        "warnings": warnings,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(output_payload, file_obj, indent=2, ensure_ascii=False)

    print(f"Saved relation definition map to: {output_path}")
    print(f"Extracted relations: {len(relation_map)}")
    if warnings:
        print(f"Warnings: {len(warnings)}")


if __name__ == "__main__":
    main()
