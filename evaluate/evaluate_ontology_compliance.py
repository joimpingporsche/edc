import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple


Triple = Tuple[str, str, str]


def _read_non_empty_lines(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8") as file_obj:
        return [line.strip() for line in file_obj if line.strip()]


def _to_str(value) -> str:
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_line_to_triples(line: str, line_no: int, source_name: str) -> Tuple[List[Triple], List[str]]:
    triples: List[Triple] = []
    warnings: List[str] = []

    try:
        parsed = ast.literal_eval(line)
    except Exception as exc:
        return [], [f"{source_name}: line {line_no}: cannot parse line with ast.literal_eval ({exc})."]

    if not isinstance(parsed, list):
        return [], [f"{source_name}: line {line_no}: expected a list, got {type(parsed).__name__}."]

    for item_idx, item in enumerate(parsed):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            warnings.append(
                f"{source_name}: line {line_no}: item {item_idx} ignored because it is not a triple of length 3."
            )
            continue
        triples.append((_to_str(item[0]), _to_str(item[1]), _to_str(item[2])))

    return triples, warnings


def _normalize_label(text: str) -> str:
    # Remove optional RDF-like language tags if they leak into plain text labels.
    # Examples: Business Capability@en, "Business Capability"@en
    text = re.sub(r"@([a-z]{2,3}(?:-[a-z0-9]+)?)$", "", str(text).strip(), flags=re.IGNORECASE)

    # Drop wrapping quotes if present.
    text = text.strip("\"'")

    # Split camelCase and acronym boundaries.
    # relToParent -> rel To Parent
    # ITComponent -> IT Component
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)

    text = text.replace("&", " and ")
    text = re.sub(r"[_\-/]+", " ", text)
    text = text.casefold()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_triple(triple: Triple) -> Triple:
    return (_normalize_label(triple[0]), _normalize_label(triple[1]), _normalize_label(triple[2]))


def _load_ontology(ontology_path: Path) -> Tuple[Set[Triple], List[str]]:
    lines = _read_non_empty_lines(ontology_path)
    warnings: List[str] = []

    if not lines:
        raise ValueError(f"Ontology file is empty: {ontology_path}")

    if len(lines) > 1:
        warnings.append(
            f"Ontology file contains {len(lines)} non-empty lines. All lines will be merged into one ontology set."
        )

    ontology_triples: Set[Triple] = set()
    for idx, line in enumerate(lines, start=1):
        triples, parse_warnings = _parse_line_to_triples(line, idx, str(ontology_path))
        ontology_triples.update(triples)
        warnings.extend(parse_warnings)

    if not ontology_triples:
        raise ValueError(f"No valid ontology triples parsed from: {ontology_path}")

    return ontology_triples, warnings


def _load_predictions(pred_path: Path) -> Tuple[List[List[Triple]], List[str]]:
    lines = _read_non_empty_lines(pred_path)
    warnings: List[str] = []
    per_line_triples: List[List[Triple]] = []

    if not lines:
        raise ValueError(f"Prediction file is empty: {pred_path}")

    for idx, line in enumerate(lines, start=1):
        triples, parse_warnings = _parse_line_to_triples(line, idx, str(pred_path))
        per_line_triples.append(triples)
        warnings.extend(parse_warnings)

    return per_line_triples, warnings


def _load_alignment_map(alignment_path: Path) -> Tuple[Dict[str, str], List[str]]:
    warnings: List[str] = []

    with alignment_path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if not isinstance(payload, dict):
        raise ValueError(f"Alignment JSON must be an object: {alignment_path}")

    accepted = payload.get("accepted", [])
    if not isinstance(accepted, list):
        raise ValueError(f"Alignment JSON key 'accepted' must be a list: {alignment_path}")

    alignment_map: Dict[str, str] = {}
    for idx, item in enumerate(accepted):
        if not isinstance(item, dict):
            warnings.append(f"alignment: accepted[{idx}] ignored because it is not an object.")
            continue

        source_relation = item.get("system_relation")
        target_relation = item.get("best_gold_relation")
        if not source_relation or not target_relation:
            warnings.append(f"alignment: accepted[{idx}] ignored because mapping fields are missing.")
            continue

        source_norm = _normalize_label(_to_str(source_relation))
        target_norm = _normalize_label(_to_str(target_relation))
        if not source_norm or not target_norm:
            warnings.append(f"alignment: accepted[{idx}] ignored because normalized mapping is empty.")
            continue

        alignment_map[source_norm] = target_norm

    return alignment_map, warnings


def evaluate(
    pred_path: Path,
    ontology_path: Path,
    max_invalid_examples: int = 50,
    alignment_path: Optional[Path] = None,
) -> Dict:
    ontology_triples, ontology_warnings = _load_ontology(ontology_path)
    pred_per_line, pred_warnings = _load_predictions(pred_path)

    alignment_map_norm: Dict[str, str] = {}
    alignment_warnings: List[str] = []
    if alignment_path is not None:
        alignment_map_norm, alignment_warnings = _load_alignment_map(alignment_path)

    ontology_triples_norm = {_normalize_triple(t) for t in ontology_triples}

    ontology_relations_norm = {_normalize_label(t[1]) for t in ontology_triples}
    relation_domains_norm: Dict[str, Set[str]] = defaultdict(set)
    relation_ranges_norm: Dict[str, Set[str]] = defaultdict(set)
    for subj, rel, obj in ontology_triples:
        rel_norm = _normalize_label(rel)
        relation_domains_norm[rel_norm].add(_normalize_label(subj))
        relation_ranges_norm[rel_norm].add(_normalize_label(obj))

    all_pred_triples = [triple for line_triples in pred_per_line for triple in line_triples]
    all_pred_triples_norm = [_normalize_triple(t) for t in all_pred_triples]

    total_pred = len(all_pred_triples)
    unique_pred = len(set(all_pred_triples))
    duplicate_pred = total_pred - unique_pred

    strict_valid = 0
    normalized_valid = 0
    relation_known = 0
    relation_known_semantic = 0
    relation_aligned = 0
    domain_valid = 0
    range_valid = 0
    domain_valid_semantic = 0
    range_valid_semantic = 0

    reason_counter = Counter()
    invalid_examples: List[Dict[str, str]] = []

    for triple, triple_norm in zip(all_pred_triples, all_pred_triples_norm):
        subj, rel, obj = triple
        subj_norm, rel_norm, obj_norm = triple_norm

        is_strict_valid = triple in ontology_triples
        is_normalized_valid = triple_norm in ontology_triples_norm

        if is_strict_valid:
            strict_valid += 1
        if is_normalized_valid:
            normalized_valid += 1

        rel_exists = rel_norm in ontology_relations_norm
        rel_effective_norm = rel_norm
        rel_aligned = False
        if (not rel_exists) and rel_norm in alignment_map_norm:
            mapped_rel_norm = alignment_map_norm[rel_norm]
            if mapped_rel_norm in ontology_relations_norm:
                rel_effective_norm = mapped_rel_norm
                rel_aligned = True

        rel_exists_semantic = rel_exists or rel_aligned

        if rel_exists:
            relation_known += 1
            if subj_norm in relation_domains_norm[rel_norm]:
                domain_valid += 1
            if obj_norm in relation_ranges_norm[rel_norm]:
                range_valid += 1

        if rel_exists_semantic:
            relation_known_semantic += 1
            if rel_aligned:
                relation_aligned += 1
            if subj_norm in relation_domains_norm[rel_effective_norm]:
                domain_valid_semantic += 1
            if obj_norm in relation_ranges_norm[rel_effective_norm]:
                range_valid_semantic += 1

        if not is_normalized_valid:
            if not rel_exists_semantic:
                reason = "unknown_relation"
            else:
                subj_ok = subj_norm in relation_domains_norm[rel_effective_norm]
                obj_ok = obj_norm in relation_ranges_norm[rel_effective_norm]

                if rel_aligned:
                    if not subj_ok and not obj_ok:
                        reason = "aligned_relation_but_subject_and_object_not_allowed"
                    elif not subj_ok:
                        reason = "aligned_relation_but_subject_not_allowed"
                    elif not obj_ok:
                        reason = "aligned_relation_but_object_not_allowed"
                    else:
                        reason = "aligned_relation_and_arguments_allowed_but_triple_not_in_ontology"
                else:
                    if not subj_ok and not obj_ok:
                        reason = "known_relation_but_subject_and_object_not_allowed"
                    elif not subj_ok:
                        reason = "known_relation_but_subject_not_allowed"
                    elif not obj_ok:
                        reason = "known_relation_but_object_not_allowed"
                    else:
                        reason = "known_relation_and_arguments_allowed_but_triple_not_in_ontology"

            reason_counter[reason] += 1
            if len(invalid_examples) < max_invalid_examples:
                invalid_examples.append(
                    {
                        "subject": subj,
                        "predicate": rel,
                        "object": obj,
                        "reason": reason,
                        "mapped_predicate": rel_effective_norm if rel_aligned else None,
                    }
                )

    ontology_covered = len(set(all_pred_triples_norm).intersection(ontology_triples_norm))

    strict_precision = (strict_valid / total_pred) if total_pred else 0.0
    normalized_precision = (normalized_valid / total_pred) if total_pred else 0.0
    ontology_coverage = (ontology_covered / len(ontology_triples_norm)) if ontology_triples_norm else 0.0
    relation_valid_rate = (relation_known / total_pred) if total_pred else 0.0
    relation_valid_rate_semantic = (relation_known_semantic / total_pred) if total_pred else 0.0
    domain_valid_rate = (domain_valid / total_pred) if total_pred else 0.0
    domain_valid_rate_semantic = (domain_valid_semantic / total_pred) if total_pred else 0.0
    range_valid_rate = (range_valid / total_pred) if total_pred else 0.0
    range_valid_rate_semantic = (range_valid_semantic / total_pred) if total_pred else 0.0

    result = {
        "input": {
            "prediction_file": str(pred_path),
            "ontology_file": str(ontology_path),
            "alignment_file": str(alignment_path) if alignment_path else None,
        },
        "counts": {
            "prediction_lines": len(pred_per_line),
            "prediction_triples_total": total_pred,
            "prediction_triples_unique": unique_pred,
            "prediction_triples_duplicates": duplicate_pred,
            "ontology_triples_total": len(ontology_triples),
            "ontology_relations_total": len(ontology_relations_norm),
            "ontology_entities_total": len({_normalize_label(x) for t in ontology_triples for x in (t[0], t[2])}),
        },
        "metrics": {
            "strict_precision_exact_triple": round(strict_precision, 6),
            "normalized_precision_exact_triple": round(normalized_precision, 6),
            "relation_valid_rate": round(relation_valid_rate, 6),
            "relation_valid_rate_semantic": round(relation_valid_rate_semantic, 6),
            "domain_valid_rate": round(domain_valid_rate, 6),
            "domain_valid_rate_semantic": round(domain_valid_rate_semantic, 6),
            "range_valid_rate": round(range_valid_rate, 6),
            "range_valid_rate_semantic": round(range_valid_rate_semantic, 6),
            "ontology_coverage_by_predictions": round(ontology_coverage, 6),
        },
        "diagnostics": {
            "alignment_used": alignment_path is not None,
            "alignment_mappings_total": len(alignment_map_norm),
            "aligned_relations_in_predictions": relation_aligned,
            "invalid_reason_counts": dict(reason_counter),
            "invalid_examples": invalid_examples,
            "warnings": ontology_warnings + pred_warnings + alignment_warnings,
        },
    }
    return result


def _print_summary(result: Dict) -> None:
    counts = result["counts"]
    metrics = result["metrics"]
    diagnostics = result["diagnostics"]

    print("=== Ontology Compliance Evaluation ===")
    print(f"prediction_file: {result['input']['prediction_file']}")
    print(f"ontology_file:   {result['input']['ontology_file']}")
    print()

    print("Counts")
    print(f"- prediction_lines:             {counts['prediction_lines']}")
    print(f"- prediction_triples_total:     {counts['prediction_triples_total']}")
    print(f"- prediction_triples_unique:    {counts['prediction_triples_unique']}")
    print(f"- prediction_triples_duplicates:{counts['prediction_triples_duplicates']}")
    print(f"- ontology_triples_total:       {counts['ontology_triples_total']}")
    print(f"- ontology_relations_total:     {counts['ontology_relations_total']}")
    print()

    print("Metrics")
    print(f"- strict_precision_exact_triple:      {metrics['strict_precision_exact_triple']}")
    print(f"- normalized_precision_exact_triple:  {metrics['normalized_precision_exact_triple']}")
    print(f"- relation_valid_rate:                {metrics['relation_valid_rate']}")
    print(f"- relation_valid_rate_semantic:       {metrics['relation_valid_rate_semantic']}")
    print(f"- domain_valid_rate:                  {metrics['domain_valid_rate']}")
    print(f"- domain_valid_rate_semantic:         {metrics['domain_valid_rate_semantic']}")
    print(f"- range_valid_rate:                   {metrics['range_valid_rate']}")
    print(f"- range_valid_rate_semantic:          {metrics['range_valid_rate_semantic']}")
    print(f"- ontology_coverage_by_predictions:   {metrics['ontology_coverage_by_predictions']}")
    print()

    print("Alignment")
    print(f"- alignment_used:                     {diagnostics['alignment_used']}")
    print(f"- alignment_mappings_total:           {diagnostics['alignment_mappings_total']}")
    print(f"- aligned_relations_in_predictions:   {diagnostics['aligned_relations_in_predictions']}")
    print()

    print("Invalid reasons")
    if diagnostics["invalid_reason_counts"]:
        for reason, count in sorted(diagnostics["invalid_reason_counts"].items(), key=lambda x: (-x[1], x[0])):
            print(f"- {reason}: {count}")
    else:
        print("- none")

    if diagnostics["warnings"]:
        print()
        print(f"Warnings ({len(diagnostics['warnings'])})")
        for warning in diagnostics["warnings"][:20]:
            print(f"- {warning}")
        if len(diagnostics["warnings"]) > 20:
            print(f"- ... {len(diagnostics['warnings']) - 20} more warnings omitted")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate EDC canon_kg predictions against a global ontology file. "
            "Designed for multi-line predictions and ontology-style gold standards."
        )
    )
    parser.add_argument("--edc_output", required=True, help="Path to canon_kg.txt produced by EDC.")
    parser.add_argument("--reference", required=True, help="Path to ontology gold file.")
    parser.add_argument(
        "--max_invalid_examples",
        type=int,
        default=50,
        help="Number of invalid triple examples to include in diagnostics.",
    )
    parser.add_argument(
        "--save_json",
        default=None,
        help="Optional path to save full evaluation result as JSON.",
    )
    parser.add_argument(
        "--alignment_json",
        default=None,
        help="Optional path to relation alignment JSON produced by align_relation_definitions.py.",
    )

    args = parser.parse_args()

    pred_path = Path(args.edc_output)
    ontology_path = Path(args.reference)
    alignment_path = Path(args.alignment_json) if args.alignment_json else None

    if not pred_path.exists():
        raise FileNotFoundError(f"Prediction file not found: {pred_path}")
    if not ontology_path.exists():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
    if alignment_path is not None and not alignment_path.exists():
        raise FileNotFoundError(f"Alignment file not found: {alignment_path}")

    result = evaluate(
        pred_path,
        ontology_path,
        max_invalid_examples=args.max_invalid_examples,
        alignment_path=alignment_path,
    )
    _print_summary(result)

    if args.save_json:
        save_path = Path(args.save_json)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("w", encoding="utf-8") as file_obj:
            json.dump(result, file_obj, indent=2, ensure_ascii=False)
        print()
        print(f"Saved JSON report to: {save_path}")


if __name__ == "__main__":
    main()