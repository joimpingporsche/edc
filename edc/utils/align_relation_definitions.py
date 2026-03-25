import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from edc.utils.llm_utils import AzureEmbeddingModel


def _load_relation_map(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if not isinstance(payload, dict) or "relation_definitions" not in payload:
        raise ValueError(f"Expected JSON object with key 'relation_definitions' in {path}")

    relation_definitions = payload["relation_definitions"]
    if not isinstance(relation_definitions, dict):
        raise ValueError(f"Expected 'relation_definitions' to be a dict in {path}")

    cleaned: Dict[str, str] = {}
    for relation, definition in relation_definitions.items():
        relation_norm = str(relation).strip()
        definition_norm = " ".join(str(definition).strip().split())
        if relation_norm and definition_norm:
            cleaned[relation_norm] = definition_norm

    return cleaned


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _build_text(relation: str, definition: str, use_relation_name: bool) -> str:
    if use_relation_name:
        return f"{relation}: {definition}"
    return definition


def _encode_with_sentence_transformers(texts: list[str], model_name: str) -> np.ndarray:
    # Lazy import so Azure mode does not require sentence-transformers installation in every env.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True)
    return np.asarray(embeddings, dtype=np.float32)


def _encode_with_azure_openai(texts: list[str], deployment_name: str, api_version: Optional[str]) -> np.ndarray:
    model = AzureEmbeddingModel(deployment_name=deployment_name, api_version=api_version)
    vectors = [model.encode(text) for text in texts]
    return np.asarray(vectors, dtype=np.float32)


def _encode_texts(
    texts: list[str],
    embedding_backend: str,
    st_model_name: str,
    azure_deployment: Optional[str],
    azure_api_version: Optional[str],
) -> np.ndarray:
    if embedding_backend == "sentence_transformers":
        return _encode_with_sentence_transformers(texts, st_model_name)

    if embedding_backend == "azure_openai":
        if not azure_deployment:
            raise ValueError("--azure_deployment is required when --embedding_backend azure_openai is used.")
        return _encode_with_azure_openai(texts, azure_deployment, azure_api_version)

    raise ValueError(f"Unsupported embedding backend: {embedding_backend}")


def align_relations(
    system_map: Dict[str, str],
    gold_map: Dict[str, str],
    embedding_backend: str,
    st_model_name: str,
    azure_deployment: Optional[str],
    azure_api_version: Optional[str],
    top_k: int,
    min_similarity: float,
    min_margin: float,
    use_relation_name: bool,
) -> Dict:
    system_relations = sorted(system_map.keys())
    gold_relations = sorted(gold_map.keys())

    system_texts = [_build_text(rel, system_map[rel], use_relation_name) for rel in system_relations]
    gold_texts = [_build_text(rel, gold_map[rel], use_relation_name) for rel in gold_relations]

    system_emb = _encode_texts(
        texts=system_texts,
        embedding_backend=embedding_backend,
        st_model_name=st_model_name,
        azure_deployment=azure_deployment,
        azure_api_version=azure_api_version,
    )
    gold_emb = _encode_texts(
        texts=gold_texts,
        embedding_backend=embedding_backend,
        st_model_name=st_model_name,
        azure_deployment=azure_deployment,
        azure_api_version=azure_api_version,
    )

    system_emb = _l2_normalize(np.asarray(system_emb, dtype=np.float32))
    gold_emb = _l2_normalize(np.asarray(gold_emb, dtype=np.float32))

    similarity = system_emb @ gold_emb.T

    accepted = []
    rejected = []

    exact_name_overlap = 0
    for rel in system_relations:
        if rel in gold_map:
            exact_name_overlap += 1

    for i, src_rel in enumerate(system_relations):
        row = similarity[i]
        ranked_indices = np.argsort(-row)
        candidate_indices = ranked_indices[:top_k]

        candidates = []
        for idx in candidate_indices:
            candidates.append(
                {
                    "gold_relation": gold_relations[idx],
                    "similarity": float(row[idx]),
                    "gold_definition": gold_map[gold_relations[idx]],
                }
            )

        best_score = float(row[candidate_indices[0]]) if len(candidate_indices) > 0 else -1.0
        second_score = float(row[candidate_indices[1]]) if len(candidate_indices) > 1 else None
        margin = (best_score - second_score) if second_score is not None else None

        passes_similarity = best_score >= min_similarity
        passes_margin = True if margin is None else margin >= min_margin

        record = {
            "system_relation": src_rel,
            "system_definition": system_map[src_rel],
            "best_gold_relation": candidates[0]["gold_relation"] if candidates else None,
            "best_similarity": best_score,
            "margin_to_second": margin,
            "candidates": candidates,
        }

        if passes_similarity and passes_margin:
            accepted.append(record)
        else:
            fail_reasons = []
            if not passes_similarity:
                fail_reasons.append("below_min_similarity")
            if not passes_margin:
                fail_reasons.append("below_min_margin")
            record["rejection_reasons"] = fail_reasons
            rejected.append(record)

    return {
        "summary": {
            "system_relations_total": len(system_relations),
            "gold_relations_total": len(gold_relations),
            "exact_name_overlap": exact_name_overlap,
            "accepted_mappings": len(accepted),
            "rejected_mappings": len(rejected),
            "config": {
                "embedding_backend": embedding_backend,
                "sentence_transformer_model": st_model_name if embedding_backend == "sentence_transformers" else None,
                "azure_deployment": azure_deployment if embedding_backend == "azure_openai" else None,
                "azure_api_version": azure_api_version if embedding_backend == "azure_openai" else None,
                "top_k": top_k,
                "min_similarity": min_similarity,
                "min_margin": min_margin,
                "use_relation_name_in_text": use_relation_name,
            },
        },
        "accepted": accepted,
        "rejected": rejected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Align system relation definitions to gold relation definitions using embedding similarity."
    )
    parser.add_argument(
        "--system",
        default="output/all_combined4/iter0/relation_definitions.json",
        help="Path to relation definitions extracted from system output.",
    )
    parser.add_argument(
        "--gold",
        default="datasets/intern/gold/leanix_relation_definitions_from_ttl.json",
        help="Path to relation definitions extracted from gold ontology TTL.",
    )
    parser.add_argument(
        "--output",
        default="output/all_combined4/relation_definition_alignment.json",
        help="Output JSON path for alignment report.",
    )
    parser.add_argument(
        "--embedding_backend",
        choices=["sentence_transformers", "azure_openai"],
        default="sentence_transformers",
        help="Embedding backend to use.",
    )
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name/path (used when embedding_backend=sentence_transformers).",
    )
    parser.add_argument(
        "--azure_deployment",
        default=None,
        help="Azure OpenAI embedding deployment name (required when embedding_backend=azure_openai).",
    )
    parser.add_argument(
        "--azure_api_version",
        default=None,
        help="Optional Azure OpenAI API version override. If omitted, env/default from adapter is used.",
    )
    parser.add_argument("--top_k", type=int, default=3, help="Top-k candidates per relation to store.")
    parser.add_argument(
        "--min_similarity",
        type=float,
        default=0.7,
        help="Minimum similarity required to accept a mapping.",
    )
    parser.add_argument(
        "--min_margin",
        type=float,
        default=0.03,
        help="Minimum gap between top-1 and top-2 similarity required to accept a mapping.",
    )
    parser.add_argument(
        "--definition_only",
        action="store_true",
        help="Use only definitions for embedding text (exclude relation names).",
    )
    args = parser.parse_args()

    system_path = Path(args.system)
    gold_path = Path(args.gold)
    output_path = Path(args.output)

    if not system_path.exists():
        raise FileNotFoundError(f"System definitions file not found: {system_path}")
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold definitions file not found: {gold_path}")

    system_map = _load_relation_map(system_path)
    gold_map = _load_relation_map(gold_path)

    report = align_relations(
        system_map=system_map,
        gold_map=gold_map,
        embedding_backend=args.embedding_backend,
        st_model_name=args.model,
        azure_deployment=args.azure_deployment,
        azure_api_version=args.azure_api_version,
        top_k=args.top_k,
        min_similarity=args.min_similarity,
        min_margin=args.min_margin,
        use_relation_name=not args.definition_only,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, indent=2, ensure_ascii=False)

    summary = report["summary"]
    print(f"Saved alignment report to: {output_path}")
    print(f"Accepted mappings: {summary['accepted_mappings']} / {summary['system_relations_total']}")


if __name__ == "__main__":
    main()
