import argparse
import ast
import csv
import json
import random
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


Triple = Tuple[str, str, str]

DOMAIN_RANGE_REASONS = {
    "known_relation_but_subject_and_object_not_allowed",
    "known_relation_but_subject_not_allowed",
    "known_relation_but_object_not_allowed",
    "aligned_relation_but_subject_and_object_not_allowed",
    "aligned_relation_but_subject_not_allowed",
    "aligned_relation_but_object_not_allowed",
}


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
    text = re.sub(r"@([a-z]{2,3}(?:-[a-z0-9]+)?)$", "", str(text).strip(), flags=re.IGNORECASE)
    text = text.strip("\"'")
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


def _load_stage_entries(path: Optional[Path]) -> Tuple[List[Dict], List[str]]:
    if path is None:
        return [], []

    warnings: List[str] = []
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, list):
        raise ValueError(f"result_at_each_stage JSON must be a list: {path}")

    entries: List[Dict] = []
    for idx, item in enumerate(payload):
        if isinstance(item, dict):
            entries.append(item)
        else:
            warnings.append(f"result_at_each_stage: entry {idx} ignored because it is not an object.")
    return entries, warnings


def _load_relation_alignment_index(alignment_path: Optional[Path]) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    if alignment_path is None:
        return {}, []

    warnings: List[str] = []
    with alignment_path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if not isinstance(payload, dict):
        raise ValueError(f"Alignment JSON must be an object: {alignment_path}")

    relation_index: Dict[str, Dict[str, float]] = defaultdict(dict)

    def _ingest_items(items: List[Dict], source_key: str) -> None:
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            system_rel = item.get("system_relation")
            if not system_rel:
                continue
            sys_norm = _normalize_label(system_rel)
            if not sys_norm:
                continue

            candidates = item.get("candidates", [])
            if isinstance(candidates, list):
                for cand in candidates:
                    if not isinstance(cand, dict):
                        continue
                    gold_rel = cand.get("gold_relation")
                    sim = cand.get("similarity")
                    if gold_rel is None or sim is None:
                        continue
                    gold_norm = _normalize_label(gold_rel)
                    if not gold_norm:
                        continue
                    try:
                        score = float(sim)
                    except Exception:
                        continue
                    prev = relation_index[sys_norm].get(gold_norm, float("-inf"))
                    relation_index[sys_norm][gold_norm] = max(prev, score)

            best_gold = item.get("best_gold_relation")
            best_sim = item.get("best_similarity")
            if best_gold is not None and best_sim is not None:
                gold_norm = _normalize_label(best_gold)
                if gold_norm:
                    try:
                        score = float(best_sim)
                        prev = relation_index[sys_norm].get(gold_norm, float("-inf"))
                        relation_index[sys_norm][gold_norm] = max(prev, score)
                    except Exception:
                        warnings.append(f"alignment:{source_key}[{idx}] best_similarity is not numeric.")

    _ingest_items(payload.get("accepted", []), "accepted")
    _ingest_items(payload.get("rejected", []), "rejected")

    return dict(relation_index), warnings


def _token_jaccard(a: str, b: str) -> float:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens.intersection(b_tokens))
    union = len(a_tokens.union(b_tokens))
    return inter / union if union else 0.0


def _entity_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    jac = _token_jaccard(a, b)
    return max(seq, jac)


def _relation_candidates(
    pred_rel_norm: str,
    gold_relations_norm: Set[str],
    relation_alignment_index: Dict[str, Dict[str, float]],
    relation_threshold: float,
) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}

    if pred_rel_norm in gold_relations_norm:
        scores[pred_rel_norm] = 1.0

    if pred_rel_norm in relation_alignment_index:
        for gold_rel_norm, sim in relation_alignment_index[pred_rel_norm].items():
            if gold_rel_norm in gold_relations_norm and sim >= relation_threshold:
                prev = scores.get(gold_rel_norm, float("-inf"))
                scores[gold_rel_norm] = max(prev, float(sim))

    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def _entity_candidates(
    pred_entity_norm: str,
    gold_entities_norm: List[str],
    entity_threshold: float,
    cache: Dict[str, List[Tuple[str, float]]],
) -> List[Tuple[str, float]]:
    if pred_entity_norm in cache:
        return cache[pred_entity_norm]

    candidates: List[Tuple[str, float]] = []
    for gold_entity in gold_entities_norm:
        sim = _entity_similarity(pred_entity_norm, gold_entity)
        if sim >= entity_threshold:
            candidates.append((gold_entity, float(sim)))

    candidates.sort(key=lambda x: (-x[1], x[0]))
    cache[pred_entity_norm] = candidates
    return candidates


def _build_prediction_records(pred_per_line: List[List[Triple]], stage_entries: List[Dict]) -> List[Dict]:
    records: List[Dict] = []
    idx = 0
    for line_idx, triples in enumerate(pred_per_line):
        stage_entry = stage_entries[line_idx] if line_idx < len(stage_entries) else {}
        for triple in triples:
            norm = _normalize_triple(triple)
            records.append(
                {
                    "pred_id": idx,
                    "line_idx": line_idx,
                    "subject": triple[0],
                    "predicate": triple[1],
                    "object": triple[2],
                    "subject_norm": norm[0],
                    "predicate_norm": norm[1],
                    "object_norm": norm[2],
                    "doc_id": stage_entry.get("doc_id"),
                    "chunk_id": stage_entry.get("chunk_id"),
                    "section_title": stage_entry.get("section_title"),
                    "source_text_snippet": (stage_entry.get("input_text") or "")[:500],
                    "legacy_reason": None,
                }
            )
            idx += 1
    return records


def _legacy_reason(
    subj_norm: str,
    rel_norm: str,
    obj_norm: str,
    ontology_relations_norm: Set[str],
    relation_domains_norm: Dict[str, Set[str]],
    relation_ranges_norm: Dict[str, Set[str]],
    relation_alignment_index: Dict[str, Dict[str, float]],
    relation_threshold: float,
) -> Tuple[str, Optional[str], bool]:
    rel_candidates = _relation_candidates(rel_norm, ontology_relations_norm, relation_alignment_index, relation_threshold)

    if rel_norm in ontology_relations_norm:
        rel_effective = rel_norm
        rel_aligned = False
        rel_exists_semantic = True
    elif rel_candidates:
        rel_effective = rel_candidates[0][0]
        rel_aligned = True
        rel_exists_semantic = True
    else:
        rel_effective = None
        rel_aligned = False
        rel_exists_semantic = False

    if not rel_exists_semantic:
        return "unknown_relation", None, False

    subj_ok = subj_norm in relation_domains_norm[rel_effective]
    obj_ok = obj_norm in relation_ranges_norm[rel_effective]

    if rel_aligned:
        if not subj_ok and not obj_ok:
            return "aligned_relation_but_subject_and_object_not_allowed", rel_effective, True
        if not subj_ok:
            return "aligned_relation_but_subject_not_allowed", rel_effective, True
        if not obj_ok:
            return "aligned_relation_but_object_not_allowed", rel_effective, True
        return "aligned_relation_and_arguments_allowed_but_triple_not_in_ontology", rel_effective, True

    if not subj_ok and not obj_ok:
        return "known_relation_but_subject_and_object_not_allowed", None, False
    if not subj_ok:
        return "known_relation_but_subject_not_allowed", None, False
    if not obj_ok:
        return "known_relation_but_object_not_allowed", None, False
    return "known_relation_and_arguments_allowed_but_triple_not_in_ontology", None, False


def _compute_alignment(
    pred_records: List[Dict],
    gold_triples_norm: Set[Triple],
    relation_alignment_index: Dict[str, Dict[str, float]],
    relation_threshold: float,
    entity_threshold: float,
) -> Dict:
    gold_triples_list = sorted(gold_triples_norm)
    gold_index = {triple: idx for idx, triple in enumerate(gold_triples_list)}
    gold_relations_norm = {t[1] for t in gold_triples_list}
    gold_entities_norm = sorted({x for t in gold_triples_list for x in (t[0], t[2])})

    entity_cache: Dict[str, List[Tuple[str, float]]] = {}

    alignable: Dict[int, Dict] = {}
    non_alignable: Dict[int, Dict] = {}
    edges: List[Dict] = []

    for record in pred_records:
        rel_cands = _relation_candidates(
            record["predicate_norm"],
            gold_relations_norm,
            relation_alignment_index,
            relation_threshold,
        )
        subj_cands = _entity_candidates(record["subject_norm"], gold_entities_norm, entity_threshold, entity_cache)
        obj_cands = _entity_candidates(record["object_norm"], gold_entities_norm, entity_threshold, entity_cache)

        rec_align = {
            **record,
            "relation_candidates": rel_cands,
            "subject_candidates": subj_cands,
            "object_candidates": obj_cands,
        }

        if not rel_cands:
            rec_align["reason_for_novelty"] = "unknown_relation"
            non_alignable[record["pred_id"]] = rec_align
            continue
        if not subj_cands or not obj_cands:
            rec_align["reason_for_novelty"] = "entity_mismatch"
            non_alignable[record["pred_id"]] = rec_align
            continue

        alignable[record["pred_id"]] = rec_align

        for rel_norm, rel_score in rel_cands:
            for subj_norm, subj_score in subj_cands:
                for obj_norm, obj_score in obj_cands:
                    triple = (subj_norm, rel_norm, obj_norm)
                    if triple in gold_index:
                        overall = (subj_score + rel_score + obj_score) / 3.0
                        edges.append(
                            {
                                "pred_id": record["pred_id"],
                                "gold_id": gold_index[triple],
                                "gold_triple": triple,
                                "overall_score": overall,
                                "subject_score": subj_score,
                                "relation_score": rel_score,
                                "object_score": obj_score,
                            }
                        )

    edges.sort(key=lambda e: (-e["overall_score"], -e["relation_score"], -e["subject_score"], -e["object_score"]))

    matched_pred: Set[int] = set()
    matched_gold: Set[int] = set()
    matched_by_pred: Dict[int, Dict] = {}

    for edge in edges:
        pid = edge["pred_id"]
        gid = edge["gold_id"]
        if pid in matched_pred or gid in matched_gold:
            continue
        matched_pred.add(pid)
        matched_gold.add(gid)
        matched_by_pred[pid] = edge

    unmatched_alignable_ids = [pid for pid in alignable if pid not in matched_by_pred]

    def _diagnose_unmatched(rec: Dict) -> str:
        subj_set = {s for s, _ in rec["subject_candidates"]}
        obj_set = {o for o, _ in rec["object_candidates"]}
        rel_set = {r for r, _ in rec["relation_candidates"]}

        for s in subj_set:
            for o in obj_set:
                for r in rel_set:
                    if (o, r, s) in gold_triples_norm:
                        return "direction_mismatch"

        for s in subj_set:
            for o in obj_set:
                if any(gt[0] == s and gt[2] == o and gt[1] not in rel_set for gt in gold_triples_norm):
                    return "relation_mismatch"

        for r in rel_set:
            if any((gt[1] == r) and ((gt[0] in subj_set) or (gt[2] in obj_set)) for gt in gold_triples_norm):
                return "entity_mismatch"

        return "threshold_not_met"

    unmatched_causes = Counter()
    unmatched_examples: Dict[str, List[Dict]] = defaultdict(list)
    for pid in unmatched_alignable_ids:
        rec = alignable[pid]
        cause = _diagnose_unmatched(rec)
        rec["reason_for_novelty"] = cause
        unmatched_causes[cause] += 1
        if len(unmatched_examples[cause]) < 20:
            unmatched_examples[cause].append(
                {
                    "subject": rec["subject"],
                    "predicate": rec["predicate"],
                    "object": rec["object"],
                    "doc_id": rec.get("doc_id"),
                    "chunk_id": rec.get("chunk_id"),
                    "section_title": rec.get("section_title"),
                }
            )

    alignable_predictions = len(alignable)
    matched = len(matched_by_pred)
    unmatched_alignable = alignable_predictions - matched
    gold_total = len(gold_triples_list)

    precision = (matched / alignable_predictions) if alignable_predictions else 0.0
    recall = (matched / gold_total) if gold_total else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "gold_triples_list": gold_triples_list,
        "alignable": alignable,
        "non_alignable": non_alignable,
        "matched_by_pred": matched_by_pred,
        "unmatched_alignable_ids": unmatched_alignable_ids,
        "metrics_alignment": {
            "alignment_precision": round(precision, 6),
            "alignment_recall": round(recall, 6),
            "alignment_f1": round(f1, 6),
            "coverage_gold": round(recall, 6),
        },
        "counts_alignment": {
            "alignable_predictions": alignable_predictions,
            "matched": matched,
            "unmatched_alignable": unmatched_alignable,
        },
        "diagnostics_alignment_unmatched": {
            "cause_counts": dict(unmatched_causes),
            "examples_top20_per_cause": dict(unmatched_examples),
        },
    }


def _build_novel_records(pred_records: List[Dict], alignment_result: Dict) -> List[Dict]:
    non_alignable = alignment_result["non_alignable"]
    alignable = alignment_result["alignable"]
    matched_by_pred = alignment_result["matched_by_pred"]

    novel: List[Dict] = []

    for _, rec in non_alignable.items():
        novel.append(rec)

    for pid in alignment_result["unmatched_alignable_ids"]:
        rec = alignable[pid]
        novel.append(rec)

    for rec in novel:
        rec["is_matched"] = rec["pred_id"] in matched_by_pred

    return novel


def _sample_novel_for_review(novel_records: List[Dict], sample_size: int, sample_seed: int) -> Tuple[List[Dict], Dict]:
    rng = random.Random(sample_seed)

    stratum_unknown = [
        r
        for r in novel_records
        if r.get("reason_for_novelty") == "unknown_relation" or r.get("legacy_reason") == "unknown_relation"
    ]
    stratum_domain_range = [r for r in novel_records if r.get("legacy_reason") in DOMAIN_RANGE_REASONS]

    target_unknown = sample_size // 2
    target_domain_range = sample_size - target_unknown

    unknown_pick = min(target_unknown, len(stratum_unknown))
    domain_pick = min(target_domain_range, len(stratum_domain_range))

    sampled: List[Dict] = []
    if unknown_pick > 0:
        sampled.extend(rng.sample(stratum_unknown, unknown_pick))
    if domain_pick > 0:
        sampled.extend(rng.sample(stratum_domain_range, domain_pick))

    remaining = sample_size - len(sampled)
    if remaining > 0:
        picked_ids = {r["pred_id"] for r in sampled}
        pool = [r for r in novel_records if r["pred_id"] not in picked_ids]
        if pool:
            sampled.extend(rng.sample(pool, min(remaining, len(pool))))

    for rec in sampled:
        rec["sample_id"] = f"{rec.get('line_idx', -1)}|{rec['subject']}|{rec['predicate']}|{rec['object']}"

    info = {
        "sample_size_requested": sample_size,
        "sample_size_exported": len(sampled),
        "sampling_seed": sample_seed,
        "strata": {
            "unknown_relation_or_unmapped_relation": len(stratum_unknown),
            "domain_range_violation": len(stratum_domain_range),
        },
        "sampled_strata": {
            "unknown_relation_or_unmapped_relation": unknown_pick,
            "domain_range_violation": domain_pick,
            "fallback_other": max(0, len(sampled) - unknown_pick - domain_pick),
        },
    }
    return sampled, info


def _read_manual_labels(labels_input: Optional[Path]) -> Tuple[Dict[str, str], List[str]]:
    if labels_input is None:
        return {}, []

    warnings: List[str] = []
    labels: Dict[str, str] = {}
    with labels_input.open("r", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        for idx, row in enumerate(reader, start=1):
            sample_id = (row.get("sample_id") or "").strip()
            label = (row.get("human_label") or row.get("label") or "").strip().upper()
            if not sample_id or not label:
                warnings.append(f"labels: row {idx} missing sample_id or label.")
                continue
            labels[sample_id] = label
    return labels, warnings


def _compute_enrichment_precision(sample_records: List[Dict], labels_map: Dict[str, str]) -> Dict:
    if not sample_records or not labels_map:
        return {
            "enrichment_precision": None,
            "enrichment_precision_strict": None,
            "label_counts": {},
        }

    label_counter = Counter()
    for rec in sample_records:
        sid = rec.get("sample_id")
        if sid in labels_map:
            label_counter[labels_map[sid]] += 1

    total_labeled = sum(label_counter.values())
    supported = label_counter.get("SUPPORTED", 0)
    unsupported = label_counter.get("UNSUPPORTED", 0)

    precision = (supported / total_labeled) if total_labeled else None
    strict_den = supported + unsupported
    precision_strict = (supported / strict_den) if strict_den else None

    return {
        "enrichment_precision": round(precision, 6) if precision is not None else None,
        "enrichment_precision_strict": round(precision_strict, 6) if precision_strict is not None else None,
        "label_counts": dict(label_counter),
    }


def _default_export_path(save_json: Optional[Path], fallback_name: str) -> Path:
    if save_json is not None:
        return save_json.parent / fallback_name
    return Path(fallback_name)


def _write_alignment_matches_csv(path: Path, pred_records: List[Dict], alignment_result: Dict) -> None:
    alignable = alignment_result["alignable"]
    non_alignable = alignment_result["non_alignable"]
    matched_by_pred = alignment_result["matched_by_pred"]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "pred_id",
                "line_idx",
                "doc_id",
                "chunk_id",
                "subject",
                "predicate",
                "object",
                "alignable",
                "matched",
                "gold_subject",
                "gold_predicate",
                "gold_object",
                "overall_score",
                "subject_score",
                "relation_score",
                "object_score",
                "reason_for_novelty",
                "legacy_reason",
            ],
        )
        writer.writeheader()

        for rec in pred_records:
            pid = rec["pred_id"]
            if pid in matched_by_pred:
                m = matched_by_pred[pid]
                gt = m["gold_triple"]
                writer.writerow(
                    {
                        "pred_id": pid,
                        "line_idx": rec.get("line_idx"),
                        "doc_id": rec.get("doc_id"),
                        "chunk_id": rec.get("chunk_id"),
                        "subject": rec["subject"],
                        "predicate": rec["predicate"],
                        "object": rec["object"],
                        "alignable": True,
                        "matched": True,
                        "gold_subject": gt[0],
                        "gold_predicate": gt[1],
                        "gold_object": gt[2],
                        "overall_score": round(m["overall_score"], 6),
                        "subject_score": round(m["subject_score"], 6),
                        "relation_score": round(m["relation_score"], 6),
                        "object_score": round(m["object_score"], 6),
                        "reason_for_novelty": "",
                        "legacy_reason": rec.get("legacy_reason"),
                    }
                )
            elif pid in alignable:
                a = alignable[pid]
                writer.writerow(
                    {
                        "pred_id": pid,
                        "line_idx": rec.get("line_idx"),
                        "doc_id": rec.get("doc_id"),
                        "chunk_id": rec.get("chunk_id"),
                        "subject": rec["subject"],
                        "predicate": rec["predicate"],
                        "object": rec["object"],
                        "alignable": True,
                        "matched": False,
                        "gold_subject": "",
                        "gold_predicate": "",
                        "gold_object": "",
                        "overall_score": "",
                        "subject_score": "",
                        "relation_score": "",
                        "object_score": "",
                        "reason_for_novelty": a.get("reason_for_novelty", ""),
                        "legacy_reason": rec.get("legacy_reason"),
                    }
                )
            else:
                n = non_alignable.get(pid, {})
                writer.writerow(
                    {
                        "pred_id": pid,
                        "line_idx": rec.get("line_idx"),
                        "doc_id": rec.get("doc_id"),
                        "chunk_id": rec.get("chunk_id"),
                        "subject": rec["subject"],
                        "predicate": rec["predicate"],
                        "object": rec["object"],
                        "alignable": False,
                        "matched": False,
                        "gold_subject": "",
                        "gold_predicate": "",
                        "gold_object": "",
                        "overall_score": "",
                        "subject_score": "",
                        "relation_score": "",
                        "object_score": "",
                        "reason_for_novelty": n.get("reason_for_novelty", "unknown"),
                        "legacy_reason": rec.get("legacy_reason"),
                    }
                )


def _write_review_sample_csv(path: Path, sample_records: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "sample_id",
                "doc_id",
                "chunk_id",
                "section_title",
                "source_text_snippet",
                "subject",
                "predicate",
                "object",
                "reason_for_novelty",
                "legacy_reason",
                "human_label",
            ],
        )
        writer.writeheader()
        for rec in sample_records:
            writer.writerow(
                {
                    "sample_id": rec.get("sample_id"),
                    "doc_id": rec.get("doc_id"),
                    "chunk_id": rec.get("chunk_id"),
                    "section_title": rec.get("section_title"),
                    "source_text_snippet": rec.get("source_text_snippet"),
                    "subject": rec.get("subject"),
                    "predicate": rec.get("predicate"),
                    "object": rec.get("object"),
                    "reason_for_novelty": rec.get("reason_for_novelty"),
                    "legacy_reason": rec.get("legacy_reason"),
                    "human_label": "",
                }
            )


def _write_top_predicates_csv(path: Path, total_counter: Counter, novel_counter: Counter) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=["scope", "predicate", "count"])
        writer.writeheader()
        for pred, count in total_counter.most_common(200):
            writer.writerow({"scope": "total_predictions", "predicate": pred, "count": count})
        for pred, count in novel_counter.most_common(200):
            writer.writerow({"scope": "novel_predictions", "predicate": pred, "count": count})


def evaluate(
    pred_path: Path,
    ontology_path: Path,
    max_invalid_examples: int = 50,
    alignment_path: Optional[Path] = None,
    relation_threshold: float = 0.85,
    entity_threshold: float = 0.85,
    sample_size: int = 100,
    sample_seed: int = 42,
    result_at_each_stage_json: Optional[Path] = None,
    labels_input: Optional[Path] = None,
):
    ontology_triples, ontology_warnings = _load_ontology(ontology_path)
    pred_per_line, pred_warnings = _load_predictions(pred_path)
    stage_entries, stage_warnings = _load_stage_entries(result_at_each_stage_json)
    relation_alignment_index, alignment_warnings = _load_relation_alignment_index(alignment_path)
    labels_map, labels_warnings = _read_manual_labels(labels_input)

    ontology_triples_norm = {_normalize_triple(t) for t in ontology_triples}
    gold_relations_norm = {_normalize_label(t[1]) for t in ontology_triples}

    relation_domains_norm: Dict[str, Set[str]] = defaultdict(set)
    relation_ranges_norm: Dict[str, Set[str]] = defaultdict(set)
    for subj, rel, obj in ontology_triples:
        rel_norm = _normalize_label(rel)
        relation_domains_norm[rel_norm].add(_normalize_label(subj))
        relation_ranges_norm[rel_norm].add(_normalize_label(obj))

    pred_records = _build_prediction_records(pred_per_line, stage_entries)

    total_pred = len(pred_records)
    unique_pred = len({(r["subject"], r["predicate"], r["object"]) for r in pred_records})
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

    for rec in pred_records:
        triple = (rec["subject"], rec["predicate"], rec["object"])
        triple_norm = (rec["subject_norm"], rec["predicate_norm"], rec["object_norm"])

        is_strict_valid = triple in ontology_triples
        is_normalized_valid = triple_norm in ontology_triples_norm
        if is_strict_valid:
            strict_valid += 1
        if is_normalized_valid:
            normalized_valid += 1

        rel_norm = rec["predicate_norm"]
        rel_exists = rel_norm in gold_relations_norm

        rel_candidates = _relation_candidates(rel_norm, gold_relations_norm, relation_alignment_index, relation_threshold)
        rel_effective = rel_norm if rel_exists else (rel_candidates[0][0] if rel_candidates else None)
        rel_aligned = (not rel_exists) and (rel_effective is not None)
        rel_exists_semantic = rel_exists or rel_aligned

        if rel_exists:
            relation_known += 1
            if rec["subject_norm"] in relation_domains_norm[rel_norm]:
                domain_valid += 1
            if rec["object_norm"] in relation_ranges_norm[rel_norm]:
                range_valid += 1

        if rel_exists_semantic:
            relation_known_semantic += 1
            if rel_aligned:
                relation_aligned += 1
            if rec["subject_norm"] in relation_domains_norm[rel_effective]:
                domain_valid_semantic += 1
            if rec["object_norm"] in relation_ranges_norm[rel_effective]:
                range_valid_semantic += 1

        if not is_normalized_valid:
            legacy_reason, mapped_predicate, _ = _legacy_reason(
                rec["subject_norm"],
                rel_norm,
                rec["object_norm"],
                gold_relations_norm,
                relation_domains_norm,
                relation_ranges_norm,
                relation_alignment_index,
                relation_threshold,
            )
            rec["legacy_reason"] = legacy_reason
            reason_counter[legacy_reason] += 1

            if len(invalid_examples) < max_invalid_examples:
                invalid_examples.append(
                    {
                        "subject": rec["subject"],
                        "predicate": rec["predicate"],
                        "object": rec["object"],
                        "reason": legacy_reason,
                        "mapped_predicate": mapped_predicate,
                    }
                )

    alignment_result = _compute_alignment(
        pred_records,
        ontology_triples_norm,
        relation_alignment_index,
        relation_threshold,
        entity_threshold,
    )

    novel_records = _build_novel_records(pred_records, alignment_result)
    for rec in novel_records:
        if rec.get("legacy_reason") is None:
            legacy_reason, _, _ = _legacy_reason(
                rec["subject_norm"],
                rec["predicate_norm"],
                rec["object_norm"],
                gold_relations_norm,
                relation_domains_norm,
                relation_ranges_norm,
                relation_alignment_index,
                relation_threshold,
            )
            rec["legacy_reason"] = legacy_reason

    sample_records, sampling_info = _sample_novel_for_review(novel_records, sample_size, sample_seed)
    enrichment_precision = _compute_enrichment_precision(sample_records, labels_map)

    ontology_covered = len({(r["subject_norm"], r["predicate_norm"], r["object_norm"]) for r in pred_records}.intersection(ontology_triples_norm))

    strict_precision = (strict_valid / total_pred) if total_pred else 0.0
    normalized_precision = (normalized_valid / total_pred) if total_pred else 0.0
    ontology_coverage = (ontology_covered / len(ontology_triples_norm)) if ontology_triples_norm else 0.0
    relation_valid_rate = (relation_known / total_pred) if total_pred else 0.0
    relation_valid_rate_semantic = (relation_known_semantic / total_pred) if total_pred else 0.0
    domain_valid_rate = (domain_valid / total_pred) if total_pred else 0.0
    domain_valid_rate_semantic = (domain_valid_semantic / total_pred) if total_pred else 0.0
    range_valid_rate = (range_valid / total_pred) if total_pred else 0.0
    range_valid_rate_semantic = (range_valid_semantic / total_pred) if total_pred else 0.0

    novel_count = len(novel_records)
    novelty_rate = (novel_count / total_pred) if total_pred else 0.0
    total_predicate_counter = Counter(r["predicate_norm"] for r in pred_records)
    novel_predicate_counter = Counter(r["predicate_norm"] for r in novel_records)

    unique_predicates_after_canonicalization = None
    if stage_entries:
        preds = set()
        for entry in stage_entries:
            triples = entry.get("schema_canonicalization", [])
            if isinstance(triples, list):
                for triple in triples:
                    if isinstance(triple, (list, tuple)) and len(triple) == 3:
                        preds.add(_normalize_label(_to_str(triple[1])))
        unique_predicates_after_canonicalization = len(preds)

    top_novel_predicates = [
        {"predicate": pred, "count": count}
        for pred, count in novel_predicate_counter.most_common(20)
    ]

    novel_examples_by_predicate = {}
    for pred, _ in novel_predicate_counter.most_common(20):
        examples = []
        for rec in novel_records:
            if rec["predicate_norm"] == pred:
                examples.append(
                    {
                        "subject": rec["subject"],
                        "predicate": rec["predicate"],
                        "object": rec["object"],
                        "reason_for_novelty": rec.get("reason_for_novelty"),
                    }
                )
            if len(examples) >= 10:
                break
        novel_examples_by_predicate[pred] = examples

    result = {
        "input": {
            "prediction_file": str(pred_path),
            "ontology_file": str(ontology_path),
            "alignment_file": str(alignment_path) if alignment_path else None,
            "result_at_each_stage_json": str(result_at_each_stage_json) if result_at_each_stage_json else None,
            "labels_input": str(labels_input) if labels_input else None,
        },
        "counts": {
            "prediction_total": total_pred,
            "prediction_lines": len(pred_per_line),
            "prediction_triples_total": total_pred,
            "prediction_triples_unique": unique_pred,
            "prediction_triples_duplicates": duplicate_pred,
            "gold_total": len(ontology_triples_norm),
            "ontology_triples_total": len(ontology_triples_norm),
            "ontology_relations_total": len(gold_relations_norm),
            "ontology_entities_total": len({x for t in ontology_triples_norm for x in (t[0], t[2])}),
            "alignable_predictions": alignment_result["counts_alignment"]["alignable_predictions"],
            "matched": alignment_result["counts_alignment"]["matched"],
            "unmatched_alignable": alignment_result["counts_alignment"]["unmatched_alignable"],
            "novel_count": novel_count,
        },
        "metrics_alignment": alignment_result["metrics_alignment"],
        "metrics_enrichment_auto": {
            "novel_count": novel_count,
            "novel_relation_count": len(novel_predicate_counter),
            "novelty_rate": round(novelty_rate, 6),
            "unique_predicates_total": len(total_predicate_counter),
            "unique_predicates_novel": len(novel_predicate_counter),
            "unique_predicates_after_canonicalization": unique_predicates_after_canonicalization,
            "top_novel_predicates": top_novel_predicates,
        },
        "metrics_enrichment_manual": enrichment_precision,
        "metrics_legacy": {
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
        "sampling_info": {
            **sampling_info,
            "strata_description": {
                "A": "unknown_relation / relation_unmapped",
                "B": "domain/range violation",
            },
        },
        "thresholds": {
            "relation_threshold": relation_threshold,
            "entity_threshold": entity_threshold,
        },
        "diagnostics": {
            "alignment_used": alignment_path is not None,
            "alignment_relations_indexed": len(relation_alignment_index),
            "invalid_reason_counts": dict(reason_counter),
            "invalid_examples": invalid_examples,
            "alignable_unmatched_cause_counts": alignment_result["diagnostics_alignment_unmatched"]["cause_counts"],
            "alignable_unmatched_examples_top20": alignment_result["diagnostics_alignment_unmatched"][
                "examples_top20_per_cause"
            ],
            "top_novel_predicates": top_novel_predicates,
            "novel_examples_by_top_predicate": novel_examples_by_predicate,
            "warnings": ontology_warnings + pred_warnings + stage_warnings + alignment_warnings + labels_warnings,
        },
        "exports": {},
    }

    return result, pred_records, alignment_result, sample_records, total_predicate_counter, novel_predicate_counter


def _print_summary(result: Dict) -> None:
    counts = result["counts"]
    metrics_alignment = result["metrics_alignment"]
    metrics_enrichment_auto = result["metrics_enrichment_auto"]
    metrics_legacy = result["metrics_legacy"]

    print("=== Two-Track Ontology Evaluation ===")
    print(f"prediction_file: {result['input']['prediction_file']}")
    print(f"ontology_file:   {result['input']['ontology_file']}")
    print()

    print("Counts")
    print(f"- prediction_total:              {counts['prediction_total']}")
    print(f"- gold_total:                    {counts['gold_total']}")
    print(f"- alignable_predictions:         {counts['alignable_predictions']}")
    print(f"- matched:                       {counts['matched']}")
    print(f"- unmatched_alignable:           {counts['unmatched_alignable']}")
    print(f"- novel_count:                   {counts['novel_count']}")
    print()

    print("Alignment metrics")
    print(f"- alignment_precision:           {metrics_alignment['alignment_precision']}")
    print(f"- alignment_recall:              {metrics_alignment['alignment_recall']}")
    print(f"- alignment_f1:                  {metrics_alignment['alignment_f1']}")
    print(f"- coverage_gold:                 {metrics_alignment['coverage_gold']}")
    print()

    print("Enrichment metrics (auto)")
    print(f"- novelty_rate:                  {metrics_enrichment_auto['novelty_rate']}")
    print(f"- novel_relation_count:          {metrics_enrichment_auto['novel_relation_count']}")
    print(f"- unique_predicates_total:       {metrics_enrichment_auto['unique_predicates_total']}")
    print(f"- unique_predicates_novel:       {metrics_enrichment_auto['unique_predicates_novel']}")
    print()

    print("Legacy metrics (secondary)")
    print(f"- strict_precision_exact_triple: {metrics_legacy['strict_precision_exact_triple']}")
    print(f"- normalized_precision_exact:    {metrics_legacy['normalized_precision_exact_triple']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Two-track evaluation for EDC outputs: alignment against ontology schema and enrichment analysis for novel facts."
        )
    )
    parser.add_argument("--edc_output", required=True, help="Path to predicted triples file.")
    parser.add_argument("--reference", required=True, help="Path to ontology gold file.")
    parser.add_argument("--alignment_json", default=None, help="Optional relation alignment JSON.")
    parser.add_argument("--result_at_each_stage_json", default=None, help="Optional result_at_each_stage.json for context.")
    parser.add_argument("--labels_input", default=None, help="Optional labeled review CSV for enrichment precision.")
    parser.add_argument("--max_invalid_examples", type=int, default=50, help="Max invalid examples in diagnostics.")
    parser.add_argument("--relation_threshold", type=float, default=0.85, help="Relation match threshold.")
    parser.add_argument("--entity_threshold", type=float, default=0.85, help="Entity match threshold.")
    parser.add_argument("--sample_size", type=int, default=100, help="Novel sample size for manual review export.")
    parser.add_argument("--sample_seed", type=int, default=42, help="Random seed for sampling.")
    parser.add_argument("--save_json", default=None, help="Optional path to save JSON report.")
    parser.add_argument("--alignment_matches_csv", default=None, help="Optional path for alignment matches CSV.")
    parser.add_argument("--review_sample_output", default=None, help="Optional path for manual review sample CSV.")
    parser.add_argument("--top_predicates_csv", default=None, help="Optional path for top predicates CSV.")

    args = parser.parse_args()

    pred_path = Path(args.edc_output)
    ontology_path = Path(args.reference)
    alignment_path = Path(args.alignment_json) if args.alignment_json else None
    stage_path = Path(args.result_at_each_stage_json) if args.result_at_each_stage_json else None
    labels_path = Path(args.labels_input) if args.labels_input else None
    save_json_path = Path(args.save_json) if args.save_json else None

    if not pred_path.exists():
        raise FileNotFoundError(f"Prediction file not found: {pred_path}")
    if not ontology_path.exists():
        raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
    if alignment_path is not None and not alignment_path.exists():
        raise FileNotFoundError(f"Alignment file not found: {alignment_path}")
    if stage_path is not None and not stage_path.exists():
        raise FileNotFoundError(f"result_at_each_stage file not found: {stage_path}")
    if labels_path is not None and not labels_path.exists():
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    result, pred_records, alignment_result, sample_records, total_counter, novel_counter = evaluate(
        pred_path=pred_path,
        ontology_path=ontology_path,
        max_invalid_examples=args.max_invalid_examples,
        alignment_path=alignment_path,
        relation_threshold=args.relation_threshold,
        entity_threshold=args.entity_threshold,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        result_at_each_stage_json=stage_path,
        labels_input=labels_path,
    )

    alignment_matches_csv = (
        Path(args.alignment_matches_csv)
        if args.alignment_matches_csv
        else _default_export_path(save_json_path, "alignment_matches.csv")
    )
    review_sample_csv = (
        Path(args.review_sample_output)
        if args.review_sample_output
        else _default_export_path(save_json_path, "novel_sample_for_manual_review.csv")
    )
    top_predicates_csv = (
        Path(args.top_predicates_csv)
        if args.top_predicates_csv
        else _default_export_path(save_json_path, "top_predicates.csv")
    )

    _write_alignment_matches_csv(alignment_matches_csv, pred_records, alignment_result)
    _write_review_sample_csv(review_sample_csv, sample_records)
    _write_top_predicates_csv(top_predicates_csv, total_counter, novel_counter)

    result["exports"] = {
        "alignment_matches_csv": str(alignment_matches_csv),
        "novel_sample_for_manual_review_csv": str(review_sample_csv),
        "top_predicates_csv": str(top_predicates_csv),
    }

    _print_summary(result)

    if save_json_path:
        save_json_path.parent.mkdir(parents=True, exist_ok=True)
        with save_json_path.open("w", encoding="utf-8") as file_obj:
            json.dump(result, file_obj, indent=2, ensure_ascii=False)
        print()
        print(f"Saved JSON report to: {save_json_path}")


if __name__ == "__main__":
    main()
