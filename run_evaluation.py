"""
run_evaluation.py – Vollautomatische Evaluations-Pipeline

Schritte:
  1. Duplikate entfernen  (deduplicate_triples.py)
  2. Evaluationslauf 1   (two_track_evaluation) → novel_sample_for_manual_review.csv
  3. LLM-Labeling        (Azure OpenAI) → ai_eval.csv
  4. Evaluationslauf 2   (two_track_evaluation mit --labels_input) → finaler JSON-Report

Beispielaufruf:
  python run_evaluation.py \
    --edc_output output/all_combined_prompt2_with_filter/iter0/useful_kg.txt \
    --reference datasets/intern/gold/leanix_ontology_tripel_cleaned.txt \
    --alignment_json output/all_combined4/relation_definition_alignment_2.json \
    --result_at_each_stage_json output/all_combined_prompt2_with_filter/iter0/result_at_each_stage.json \
    --llm gpt-4.1-mini \
    --sample_size 100
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM-Labeling
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert Enterprise Architecture ontology evaluator.
Your task is to judge whether an automatically extracted knowledge graph triple \
represents a valid, meaningful relationship within an Enterprise Architecture context.

A triple is SUPPORTED if:
- The relationship between subject and object is real, plausible, and meaningful in an EA context.
- The triple could be a useful addition to an EA ontology (even if the exact predicate wording differs slightly from canonical predicates).
- The source text snippet confirms or at least plausibly implies the relationship.

A triple is PARTIALLY_SUPPORTED if:
- The relationship direction or predicate wording is slightly off, but the core idea is correct.
- The triple captures a real relationship but with imprecise entities or predicate.
- The source text only weakly or indirectly implies the relationship.

A triple is UNSUPPORTED if:
- The relationship is wrong, nonsensical, or is an artefact of extraction errors.
- The source text does not support this relationship.
- The triple is too generic or trivially true to be useful in an EA ontology (e.g. "IT_Product is IT_Product").

Reply with exactly one word: SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED. No explanation."""


def _build_user_message(row: Dict[str, str]) -> str:
    subject = row.get("subject", "")
    predicate = row.get("predicate", "")
    obj = row.get("object", "")
    snippet = (row.get("source_text_snippet") or "").strip()
    reason = row.get("reason_for_novelty", "")

    parts = [f"Triple: [{subject!r}, {predicate!r}, {obj!r}]"]
    if reason:
        parts.append(f"Novelty reason: {reason}")
    if snippet:
        parts.append(f"Source text snippet:\n\"\"\"\n{snippet[:600]}\n\"\"\"")
    else:
        parts.append("(No source text snippet available.)")
    return "\n".join(parts)


def _call_llm(model: str, user_message: str, retries: int = 3) -> str:
    """Call AzureChatOpenAI via llm_utils and return SUPPORTED or UNSUPPORTED."""
    # Import here so the module can be used without the full edc env for --skip_dedup only runs
    from edc.utils.llm_utils import openai_chat_completion

    history = [{"role": "user", "content": user_message}]

    for attempt in range(retries):
        try:
            raw = openai_chat_completion(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                history=history,
                temperature=0,
                max_tokens=16,
            )
            label = raw.strip().upper()
            if label not in {"SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED"}:
                # Try to extract a valid label from the response
                if "PARTIALLY_SUPPORTED" in label:
                    return "PARTIALLY_SUPPORTED"
                if "UNSUPPORTED" in label:
                    return "UNSUPPORTED"
                if "SUPPORTED" in label:
                    return "SUPPORTED"
                logger.warning("Unexpected LLM response %r – treating as UNSUPPORTED", raw)
                return "UNSUPPORTED"
            return label
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning("LLM call failed (attempt %d/%d): %s – retrying in %ds", attempt + 1, retries, exc, wait)
            time.sleep(wait)

    logger.error("LLM call failed after %d retries. Defaulting to UNSUPPORTED.", retries)
    return "UNSUPPORTED"


def label_with_llm(
    review_csv: Path,
    ai_eval_csv: Path,
    model: str,
    request_delay: float = 0.3,
) -> None:
    """Read novel_sample_for_manual_review.csv, label each row via LLM, write ai_eval.csv."""
    with review_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.warning("Review CSV is empty – nothing to label.")
        ai_eval_csv.write_text("sample_id,human_label\n", encoding="utf-8")
        return

    logger.info("Labeling %d samples with %s …", len(rows), model)

    labelled: List[Dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        sample_id = row.get("sample_id", "")
        user_msg = _build_user_message(row)
        label = _call_llm(model, user_msg)
        labelled.append({"sample_id": sample_id, "human_label": label})
        logger.info("  [%d/%d] %s  →  %s", idx, len(rows), sample_id, label)
        if request_delay > 0:
            time.sleep(request_delay)

    ai_eval_csv.parent.mkdir(parents=True, exist_ok=True)
    with ai_eval_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sample_id", "human_label"])
        writer.writeheader()
        writer.writerows(labelled)

    supported = sum(1 for r in labelled if r["human_label"] == "SUPPORTED")
    partially = sum(1 for r in labelled if r["human_label"] == "PARTIALLY_SUPPORTED")
    unsupported = sum(1 for r in labelled if r["human_label"] == "UNSUPPORTED")
    logger.info(
        "Labeling done: %d SUPPORTED, %d PARTIALLY_SUPPORTED, %d UNSUPPORTED  →  %s",
        supported,
        partially,
        unsupported,
        ai_eval_csv,
    )


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], step_name: str) -> None:
    logger.info("=== %s ===", step_name)
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        logger.error("Step '%s' exited with code %d – aborting.", step_name, result.returncode)
        sys.exit(result.returncode)


def run_dedup(edc_output: Path, dedup_output: Path, scope: str) -> None:
    _run(
        [
            sys.executable, "evaluate/deduplicate_triples.py",
            "--input", str(edc_output),
            "--output", str(dedup_output),
            "--scope", scope,
        ],
        step_name="Deduplication",
    )


def run_evaluation_pass(
    edc_output: Path,
    reference: Path,
    save_json: Path,
    review_csv: Path,
    alignment_json: Optional[Path],
    result_at_each_stage_json: Optional[Path],
    labels_input: Optional[Path],
    relation_threshold: float,
    entity_threshold: float,
    sample_size: int,
    sample_seed: int,
    step_name: str,
) -> None:
    cmd = [
        sys.executable, "evaluate/evaluate_ontology_compliance.py",
        "--edc_output", str(edc_output),
        "--reference", str(reference),
        "--save_json", str(save_json),
        "--review_sample_output", str(review_csv),
        "--relation_threshold", str(relation_threshold),
        "--entity_threshold", str(entity_threshold),
        "--sample_size", str(sample_size),
        "--sample_seed", str(sample_seed),
    ]
    if alignment_json:
        cmd += ["--alignment_json", str(alignment_json)]
    if result_at_each_stage_json:
        cmd += ["--result_at_each_stage_json", str(result_at_each_stage_json)]
    if labels_input:
        cmd += ["--labels_input", str(labels_input)]
    _run(cmd, step_name=step_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vollautomatische Evaluations-Pipeline: Dedup → Eval-Pass-1 → LLM-Labeling → Eval-Pass-2"
    )
    # Required
    parser.add_argument(
        "--edc_output",
        required=True,
        help="Pfad zur KG-Ausgabedatei (z.B. output/runX/iter0/useful_kg.txt). "
             "Wird dedupliziert; das Dedup-Ergebnis wird für die Evaluation verwendet.",
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Pfad zur Gold-Ontologie (leanix_ontology_tripel_cleaned.txt).",
    )

    # Optional paths
    parser.add_argument("--alignment_json", default=None, help="Optionales Relation-Alignment-JSON.")
    parser.add_argument(
        "--result_at_each_stage_json",
        default=None,
        help="Optionales result_at_each_stage.json für Chunk-Kontext im Report.",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Ausgabeverzeichnis für alle erzeugten Dateien. "
             "Standard: Elternverzeichnis von --edc_output.",
    )

    # LLM
    parser.add_argument(
        "--llm",
        default="gpt-4.1-mini",
        help="Azure-OpenAI-Deployment-Name für das LLM-Labeling (default: gpt-4.1-mini).",
    )
    parser.add_argument(
        "--request_delay",
        type=float,
        default=0.3,
        help="Pause in Sekunden zwischen LLM-Anfragen (default: 0.3).",
    )

    # Eval parameters
    parser.add_argument("--relation_threshold", type=float, default=0.85)
    parser.add_argument("--entity_threshold", type=float, default=0.85)
    parser.add_argument("--sample_size", type=int, default=100)
    parser.add_argument("--sample_seed", type=int, default=42)

    # Dedup
    parser.add_argument(
        "--dedup_scope",
        choices=["line", "global"],
        default="global",
        help="Dedup-Scope: global = über gesamte Datei (default).",
    )
    parser.add_argument(
        "--skip_dedup",
        action="store_true",
        help="Dedup-Schritt überspringen und --edc_output direkt verwenden.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    edc_output = Path(args.edc_output)
    if not edc_output.exists():
        logger.error("--edc_output nicht gefunden: %s", edc_output)
        sys.exit(1)

    reference = Path(args.reference)
    if not reference.exists():
        logger.error("--reference nicht gefunden: %s", reference)
        sys.exit(1)

    alignment_json = Path(args.alignment_json) if args.alignment_json else None
    result_at_each_stage_json = (
        Path(args.result_at_each_stage_json) if args.result_at_each_stage_json else None
    )

    out_dir = Path(args.output_dir) if args.output_dir else edc_output.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Derived paths
    stem = edc_output.stem  # e.g. "useful_kg"
    dedup_output = out_dir / f"{stem}_dedup.txt"
    review_csv_pass1 = out_dir / "novel_sample_for_manual_review.csv"
    ai_eval_csv = out_dir / "ai_eval.csv"
    eval_json_pass1 = out_dir / "eval_report_pass1.json"
    eval_json_final = out_dir / "eval_report_final.json"
    review_csv_final = out_dir / "novel_sample_with_labels.csv"

    # ------------------------------------------------------------------
    # Step 1 – Deduplication
    # ------------------------------------------------------------------
    if args.skip_dedup:
        dedup_output = edc_output
        logger.info("Dedup übersprungen – verwende direkt: %s", dedup_output)
    else:
        run_dedup(edc_output, dedup_output, scope=args.dedup_scope)

    # ------------------------------------------------------------------
    # Step 2 – Evaluation Pass 1 (without labels → generate review CSV)
    # ------------------------------------------------------------------
    run_evaluation_pass(
        edc_output=dedup_output,
        reference=reference,
        save_json=eval_json_pass1,
        review_csv=review_csv_pass1,
        alignment_json=alignment_json,
        result_at_each_stage_json=result_at_each_stage_json,
        labels_input=None,
        relation_threshold=args.relation_threshold,
        entity_threshold=args.entity_threshold,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        step_name="Evaluation Pass 1 (ohne Labels)",
    )

    if not review_csv_pass1.exists():
        logger.error("novel_sample_for_manual_review.csv wurde nicht erzeugt: %s", review_csv_pass1)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3 – LLM Labeling
    # ------------------------------------------------------------------
    label_with_llm(
        review_csv=review_csv_pass1,
        ai_eval_csv=ai_eval_csv,
        model=args.llm,
        request_delay=args.request_delay,
    )

    # ------------------------------------------------------------------
    # Step 4 – Evaluation Pass 2 (with LLM labels → final report)
    # ------------------------------------------------------------------
    run_evaluation_pass(
        edc_output=dedup_output,
        reference=reference,
        save_json=eval_json_final,
        review_csv=review_csv_final,
        alignment_json=alignment_json,
        result_at_each_stage_json=result_at_each_stage_json,
        labels_input=ai_eval_csv,
        relation_threshold=args.relation_threshold,
        entity_threshold=args.entity_threshold,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        step_name="Evaluation Pass 2 (mit LLM-Labels – finaler Report)",
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("=== Evaluation abgeschlossen ===")
    logger.info("  Dedup-Output:      %s", dedup_output)
    logger.info("  Review-CSV:        %s", review_csv_pass1)
    logger.info("  AI-Labels:         %s", ai_eval_csv)
    logger.info("  Finaler Report:    %s", eval_json_final)


if __name__ == "__main__":
    main()
