from argparse import ArgumentParser
from edc.edc_framework import EDC
import os
import logging

os.environ["TOKENIZERS_PARALLELISM"] = "false"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--run_dc",
        default="true",
        help="Set to 'false' to skip Schema Definition and Schema Canonicalization.",
    )
    # OIE module setting
    parser.add_argument(
        "--oie_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for open information extraction."
    )
    parser.add_argument(
        "--oie_prompt_template_file_path",
        default="./prompt_templates/oie_template.txt",
        help="Promp template used for open information extraction.",
    )
    parser.add_argument(
        "--oie_few_shot_example_file_path",
        default="./few_shot_examples/example/oie_few_shot_examples.txt",
        help="Few shot examples used for open information extraction.",
    )

    # Schema Definition setting
    parser.add_argument(
        "--sd_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for schema definition."
    )
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
        help="LLM used for schema canonicaliztion verification.",
    )
    parser.add_argument(
        "--sc_embedder", default="intfloat/e5-mistral-7b-instruct", help="Embedder used for schema canonicalization. Has to be a sentence transformer. Please refer to https://sbert.net/"
    )
    parser.add_argument(
        "--sc_top_k",
        default=3,
        type=int,
        help="Number of schema candidates retrieved before LLM verification.",
    )
    parser.add_argument(
        "--sc_min_similarity",
        default=None,
        type=float,
        help="Minimum similarity required for attempting canonicalization.",
    )
    parser.add_argument(
        "--sc_min_margin",
        default=None,
        type=float,
        help="Minimum score gap between top-1 and top-2 candidates for canonicalization.",
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
        "--sr_embedder", default="intfloat/e5-mistral-7b-instruct", help="Embedding model used for schema retriever. Has to be a sentence transformer. Please refer to https://sbert.net/"
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
    parser.add_argument(
        "--ee_llm", default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM used for entity extraction."
    )
    parser.add_argument(
        "--ee_prompt_template_file_path",
        default="./prompt_templates/ee_template.txt",
        help="Prompt templated used for entity extraction.",
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

    # Triple utility filter setting
    parser.add_argument(
        "--enable_triple_utility_filter",
        action="store_true",
        help="Enable final LLM filtering step that keeps only schema-useful triplets.",
    )
    parser.add_argument(
        "--tu_llm",
        default="mistralai/Mistral-7B-Instruct-v0.2",
        help="LLM used for triple utility filtering.",
    )
    parser.add_argument(
        "--tu_prompt_template_file_path",
        default="./prompt_templates/tu_filter_template.txt",
        help="Prompt template used for triple utility filtering.",
    )
    parser.add_argument(
        "--tu_few_shot_example_file_path",
        default=None,
        help="Few-shot examples used for triple utility filtering.",
    )

    # Input setting
    parser.add_argument(
        "--input_text_file_path",
        default="./datasets/example.txt",
        help="File containing input texts to extract KG from, each line contains one piece of text.",
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

    # Output setting
    parser.add_argument("--output_dir", default="./output/tmp", help="Directory to output to.")
    parser.add_argument("--logging_verbose", action="store_const", dest="loglevel", const=logging.INFO)
    parser.add_argument("--logging_debug", action="store_const", dest="loglevel", const=logging.DEBUG)

    args = parser.parse_args()
    args = vars(args)
    edc = EDC(**args)
    

    input_text_list = open(args["input_text_file_path"], "r").readlines()
    output_kg = edc.extract_kg(
        input_text_list,
        args["output_dir"],
        refinement_iterations=args["refinement_iterations"],
    )
