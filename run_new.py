from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List
import json
import logging
import os

from edc.edc_framework import EDC
from edc.preprocessing.chunking_v1 import chunk_document as chunk_document_v1
from edc.preprocessing.chunking_v2 import chunk_document as chunk_document_v2


os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_documents(input_text_file_path: str = None, input_text_dir: str = None) -> List[Dict[str, str]]:
    if bool(input_text_file_path) == bool(input_text_dir):
        raise ValueError("Provide exactly one of --input_text_file_path or --input_text_dir.")

    documents = []

    if input_text_dir:
        base_path = Path(input_text_dir)
        if not base_path.exists() or not base_path.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_text_dir}")

        text_files = sorted(base_path.glob("*.txt"))
        if not text_files:
            raise ValueError(f"No .txt files found in input directory: {input_text_dir}")

        for text_file in text_files:
            documents.append(
                {
                    "doc_id": text_file.stem,
                    "source_path": str(text_file),
                    "text": text_file.read_text(encoding="utf-8"),
                }
            )

    else:
        source = Path(input_text_file_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Input file not found: {input_text_file_path}")

        documents.append(
            {
                "doc_id": source.stem,
                "source_path": str(source),
                "text": source.read_text(encoding="utf-8"),
            }
        )

    return documents


def build_chunks(args: Dict, documents: List[Dict[str, str]]) -> List[Dict]:
    all_chunks = []

    for document in documents:
        if args["chunking_variant"] in ["v1", "chunking1", "1", "baseline"]:
            chunks = chunk_document_v1(
                doc_id=document["doc_id"],
                text=document["text"],
                mode=args["v1_mode"],
                window_sentences=args["v1_window_sentences"],
                overlap_sentences=args["v1_overlap_sentences"],
                window_chars=args["v1_window_chars"],
                overlap_chars=args["v1_overlap_chars"],
            )
        else:
            chunks = chunk_document_v2(
                doc_id=document["doc_id"],
                text=document["text"],
                max_chunk_chars=args["v2_max_chunk_chars"],
                bullet_group_size=args["v2_bullet_group_size"],
                prose_window_sentences=args["v2_prose_window_sentences"],
                prose_overlap_sentences=args["v2_prose_overlap_sentences"],
                table_rows_per_chunk=args["v2_table_rows_per_chunk"],
            )

        for chunk in chunks:
            chunk.setdefault("meta", {})
            chunk["meta"]["source_path"] = document["source_path"]

        all_chunks.extend(chunks)

    for global_idx, chunk in enumerate(all_chunks):
        chunk["global_index"] = global_idx

    return all_chunks


def _normalize_chunking_variant_label(chunking_variant: str) -> str:
    if chunking_variant in ["v1", "chunking1", "1", "baseline"]:
        return "v1"
    return "v2"


def write_chunk_outputs(output_dir: str, chunks: List[Dict], chunking_variant: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    variant_label = _normalize_chunking_variant_label(chunking_variant)

    chunks_jsonl_path = output_path / f"chunks_{variant_label}.jsonl"
    with chunks_jsonl_path.open("w", encoding="utf-8") as file_obj:
        for chunk in chunks:
            file_obj.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    chunks_text_path = output_path / f"chunks_text_for_edc_{variant_label}.txt"
    with chunks_text_path.open("w", encoding="utf-8") as file_obj:
        for chunk in chunks:
            file_obj.write(chunk["text_for_edc"].strip().replace("\n", " "))
            file_obj.write("\n")


def extract_edc_kwargs(args: Dict) -> Dict:
    return {
        "oie_llm": args["oie_llm"],
        "oie_prompt_template_file_path": args["oie_prompt_template_file_path"],
        "oie_few_shot_example_file_path": args["oie_few_shot_example_file_path"],
        "sd_llm": args["sd_llm"],
        "sd_prompt_template_file_path": args["sd_prompt_template_file_path"],
        "sd_few_shot_example_file_path": args["sd_few_shot_example_file_path"],
        "sc_llm": args["sc_llm"],
        "sc_embedder": args["sc_embedder"],
        "embedding_api": args["embedding_api"],
        "azure_openai_api_version": args["azure_openai_api_version"],
        "sc_prompt_template_file_path": args["sc_prompt_template_file_path"],
        "sr_adapter_path": args["sr_adapter_path"],
        "sr_embedder": args["sr_embedder"],
        "oie_refine_prompt_template_file_path": args["oie_refine_prompt_template_file_path"],
        "oie_refine_few_shot_example_file_path": args["oie_refine_few_shot_example_file_path"],
        "ee_llm": args["ee_llm"],
        "ee_prompt_template_file_path": args["ee_prompt_template_file_path"],
        "ee_few_shot_example_file_path": args["ee_few_shot_example_file_path"],
        "em_prompt_template_file_path": args["em_prompt_template_file_path"],
        "target_schema_path": args["target_schema_path"],
        "enrich_schema": args["enrich_schema"],
        "loglevel": args["loglevel"],
    }


if __name__ == "__main__":
    parser = ArgumentParser()

    # OIE module setting
    parser.add_argument("--oie_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for open information extraction.")
    parser.add_argument(
        "--oie_prompt_template_file_path",
        default="./prompt_templates/oie_template.txt",
        help="Prompt template used for open information extraction.",
    )
    parser.add_argument(
        "--oie_few_shot_example_file_path",
        default="./few_shot_examples/example/oie_few_shot_examples.txt",
        help="Few shot examples used for open information extraction.",
    )

    # Schema Definition setting
    parser.add_argument("--sd_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for schema definition.")
    parser.add_argument(
        "--sd_prompt_template_file_path",
        default="./prompt_templates/sd_template.txt",
        help="Prompt template used for schema definition.",
    )
    parser.add_argument(
        "--sd_few_shot_example_file_path",
        default="./few_shot_examples/example/sd_few_shot_examples.txt",
        help="Few shot examples used for schema definition.",
    )

    # Schema Canonicalization setting
    parser.add_argument(
        "--sc_llm",
        default="mistralai/Mistral-7B-Instruct-v0.2",
        help="LLM used for schema canonicalization verification.",
    )
    parser.add_argument(
        "--sc_embedder",
        default="intfloat/e5-mistral-7b-instruct",
        help="Embedder used for schema canonicalization.",
    )
    parser.add_argument(
        "--embedding_api",
        choices=["local", "azure"],
        default="local",
        help="Embedding backend. local uses SentenceTransformer, azure uses Azure OpenAI embeddings endpoint.",
    )
    parser.add_argument(
        "--azure_openai_api_version",
        default=None,
        help="Azure OpenAI API version for embeddings. Falls back to AZURE_OPENAI_API_VERSION when omitted.",
    )
    parser.add_argument(
        "--sc_prompt_template_file_path",
        default="./prompt_templates/sc_template.txt",
        help="Prompt template used for schema canonicalization verification.",
    )

    # Refinement setting
    parser.add_argument("--sr_adapter_path", default=None, help="Path to adapter of schema retriever.")
    parser.add_argument(
        "--sr_embedder",
        default="intfloat/e5-mistral-7b-instruct",
        help="Embedding model used for schema retriever.",
    )
    parser.add_argument(
        "--oie_refine_prompt_template_file_path",
        default="./prompt_templates/oie_r_template.txt",
        help="Prompt template used for refined open information extraction.",
    )
    parser.add_argument(
        "--oie_refine_few_shot_example_file_path",
        default="./few_shot_examples/example/oie_few_shot_refine_examples.txt",
        help="Few shot examples used for refined open information extraction.",
    )
    parser.add_argument("--ee_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for entity extraction.")
    parser.add_argument(
        "--ee_prompt_template_file_path",
        default="./prompt_templates/ee_template.txt",
        help="Prompt template used for entity extraction.",
    )
    parser.add_argument(
        "--ee_few_shot_example_file_path",
        default="./few_shot_examples/example/ee_few_shot_examples.txt",
        help="Few shot examples used for entity extraction.",
    )
    parser.add_argument(
        "--em_prompt_template_file_path",
        default="./prompt_templates/em_template.txt",
        help="Prompt template used for entity merging.",
    )

    # Input setting
    parser.add_argument(
        "--input_text_file_path",
        default=None,
        help="Single input text file (mutually exclusive with --input_text_dir).",
    )
    parser.add_argument(
        "--input_text_dir",
        default=None,
        help="Directory with multiple .txt files (mutually exclusive with --input_text_file_path).",
    )
    parser.add_argument(
        "--target_schema_path",
        default="./schemas/example_schema.csv",
        help="File containing the target schema to align to.",
    )
    parser.add_argument("--refinement_iterations", default=0, type=int, help="Number of iteration to run.")
    parser.add_argument(
        "--enrich_schema",
        action="store_true",
        help="Whether un-canonicalizable relations should be added to the schema.",
    )

    # Chunking setting
    parser.add_argument(
        "--chunking_variant",
        choices=["v1", "v2", "chunking1", "chunking2", "1", "2", "baseline", "adaptive"],
        default="v1",
        help="Chunking strategy. chunking1/v1/baseline = Fixed-Window, chunking2/v2/adaptive = Adaptive Section.",
    )

    # v1 baseline settings
    parser.add_argument("--v1_mode", choices=["sentence", "char"], default="sentence")
    parser.add_argument("--v1_window_sentences", type=int, default=4)
    parser.add_argument("--v1_overlap_sentences", type=int, default=1)
    parser.add_argument("--v1_window_chars", type=int, default=1800)
    parser.add_argument("--v1_overlap_chars", type=int, default=300)

    # v2 adaptive settings
    parser.add_argument("--v2_max_chunk_chars", type=int, default=2200)
    parser.add_argument("--v2_bullet_group_size", type=int, default=6)
    parser.add_argument("--v2_prose_window_sentences", type=int, default=4)
    parser.add_argument("--v2_prose_overlap_sentences", type=int, default=1)
    parser.add_argument("--v2_table_rows_per_chunk", type=int, default=25)

    # Output setting
    parser.add_argument("--output_dir", default="./output/tmp_chunked", help="Directory to output to.")
    parser.add_argument("--logging_verbose", action="store_const", dest="loglevel", const=logging.INFO)
    parser.add_argument("--logging_debug", action="store_const", dest="loglevel", const=logging.DEBUG)
    parser.set_defaults(loglevel=logging.WARNING)

    args = vars(parser.parse_args())

    # Normalize aliases so downstream logic is explicit and stable.
    if args["chunking_variant"] in ["chunking1", "1", "baseline"]:
        args["chunking_variant"] = "v1"
    elif args["chunking_variant"] in ["chunking2", "2", "adaptive"]:
        args["chunking_variant"] = "v2"

    documents = load_documents(args["input_text_file_path"], args["input_text_dir"])
    all_chunks = build_chunks(args, documents)

    if not all_chunks:
        raise ValueError("No chunks produced. Please verify input files and chunking settings.")

    write_chunk_outputs(args["output_dir"], all_chunks, args["chunking_variant"])

    edc_kwargs = extract_edc_kwargs(args)
    edc = EDC(**edc_kwargs)

    edc_input_text_list = [chunk["text_for_edc"] for chunk in all_chunks]

    output_kg = edc.extract_kg(
        edc_input_text_list,
        args["output_dir"],
        refinement_iterations=args["refinement_iterations"],
    )
