from typing import List, Tuple
import json

import edc.utils.llm_utils as llm_utils
from transformers import AutoModelForCausalLM, AutoTokenizer


class TripleUtilityFilter:
    """Filter triplets down to schema-useful knowledge using an LLM."""

    def __init__(self, model: AutoModelForCausalLM = None, tokenizer: AutoTokenizer = None, openai_model=None) -> None:
        assert openai_model is not None or (model is not None and tokenizer is not None)
        self.model = model
        self.tokenizer = tokenizer
        self.openai_model = openai_model

    def filter_useful_triplets(
        self,
        input_triplets: List[List[str]],
        few_shot_examples_str: str,
        prompt_template_str: str,
    ) -> Tuple[List[List[str]], bool]:
        filled_prompt = prompt_template_str.format_map(
            {
                "few_shot_examples": few_shot_examples_str,
                "input_triplets": json.dumps(input_triplets, ensure_ascii=False),
            }
        )
        messages = [{"role": "user", "content": filled_prompt}]

        if self.openai_model is None:
            completion = llm_utils.generate_completion_transformers(
                messages,
                self.model,
                self.tokenizer,
                answer_prepend="Triplets: ",
            )
        else:
            completion = llm_utils.openai_chat_completion(self.openai_model, None, messages)

        filtered_triplets = llm_utils.parse_raw_triplets(completion)

        # Treat empty parse as valid only if the model explicitly emitted an empty list.
        parse_ok = bool(filtered_triplets) or ("[]" in completion)
        return filtered_triplets, parse_ok
