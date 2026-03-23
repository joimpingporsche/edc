import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict


def _normalize_text(text: str) -> str:
    return " ".join(str(text).strip().split())


def _select_longest_definition(definitions: set[str]) -> str:
    # Deterministic tie-break: if lengths match, pick lexicographically smallest.
    return sorted(definitions, key=lambda text: (-len(text), text))[0]


def extract_relation_definitions(input_path: Path) -> Dict[str, str]:
    with input_path.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)

    if not isinstance(data, list):
        raise ValueError(f"Expected top-level list in {input_path}, got {type(data).__name__}.")

    relation_to_definitions = defaultdict(set)

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        schema_definition = item.get("schema_definition", {})
        if not isinstance(schema_definition, dict):
            continue

        for relation, definition in schema_definition.items():
            relation_norm = _normalize_text(relation)
            definition_norm = _normalize_text(definition)

            if not relation_norm or not definition_norm:
                continue

            relation_to_definitions[relation_norm].add(definition_norm)

    # Convert to sorted, JSON-serializable structure with one (longest) definition per relation.
    return {
        relation: _select_longest_definition(definitions)
        for relation, definitions in sorted(relation_to_definitions.items(), key=lambda x: x[0])
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract all relation definitions from result_at_each_stage.json into a new JSON file."
    )
    parser.add_argument(
        "--input",
        default="output/all_combined4/iter0/result_at_each_stage.json",
        help="Path to result_at_each_stage.json",
    )
    parser.add_argument(
        "--output",
        default="output/all_combined4/iter0/relation_definitions.json",
        help="Output path for extracted relation definitions",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    relation_definitions = extract_relation_definitions(input_path)

    output = {
        "input_file": str(input_path),
        "relations_total": len(relation_definitions),
        "relation_definitions": relation_definitions,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(output, file_obj, indent=2, ensure_ascii=False)

    print(f"Saved relation definitions to: {output_path}")
    print(f"Extracted relations: {len(relation_definitions)}")


if __name__ == "__main__":
    main()
