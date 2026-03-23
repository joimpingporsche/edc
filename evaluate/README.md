# Evaluation

To run evaluation, run

```
python evaluation_script.py --edc_output /path/to/edc_output.txt --reference /path/to/reference.txt --max_length_diff N
```

The evaluation script is adopted from the [WebNLG evaluation script](https://github.com/WebNLG/WebNLG-Text-to-triples). It is to be noted that the evaluation script works by enumerating or possible alignment between the output triplets and reference triplets, so the evaluation speed may be very slow, this is expected. You may pass a `max_length_diff` to filter out some triplets for faster evaluation.

### Ontology Compliance Evaluation (for global ontology gold files)

If your reference file is a global ontology (for example one line with all allowed schema triples) and your EDC output is multi-line chunked predictions, use:

```
python evaluate_ontology_compliance.py \
	--edc_output /path/to/canon_kg.txt \
	--reference /path/to/ontology_gold.txt \
	--max_invalid_examples 50 \
	--save_json /optional/path/to/report.json
```

This script is intended for schema/ontology-style validation and reports:

- strict exact-triple precision
- normalized exact-triple precision (case/format tolerant)
- relation validity rate (predicate exists in ontology)
- domain/range validity rates for known relations
- ontology coverage by predictions
- invalid reason breakdown with examples