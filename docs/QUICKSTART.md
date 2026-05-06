# EDC Quickstart Guide

Schnellanleitung für einen vollständigen EDC-Lauf mit `run_new.py`.

---

## Voraussetzungen

1. **Conda-Umgebung aktivieren:**
   ```bash
   # macOS
   conda env create -f mac_environment.yml
   # Linux (GPU)
   conda env create -f environment.yml

   conda activate edc
   ```

2. **Azure OpenAI Umgebungsvariablen setzen:**
   ```bash
   export AZURE_OPENAI_ENDPOINT="https://<endpoint>.openai.azure.com/"
   export AZURE_OPENAI_API_KEY="<api-key>"
   export AZURE_OPENAI_API_VERSION="2024-02-01"
   ```

3. **Eingabedaten vorhanden** in `./datasets/intern/text/2_preprocessed/` (vorverarbeitete `*_combined*.txt`-Dateien).

---

## Quickstart-Befehl

```bash
python run_new.py \
  --chunking_variant chunking2 \
  --embedding_api azure \
  --oie_llm gpt-4.1-mini \
  --oie_few_shot_example_file_path ./few_shot_examples/example/oie_few_shot_schema_level.txt \
  --oie_prompt_template_file_path ./prompt_templates/oie_schema_level2.txt \
  --sd_llm gpt-4.1-mini \
  --sd_few_shot_example_file_path ./few_shot_examples/example/sd_few_shot_examples.txt \
  --sc_llm gpt-4.1-mini \
  --ee_llm gpt-4.1-mini \
  --sc_embedder text-embedding-3-large \
  --sr_embedder text-embedding-3-large \
  --sc_top_k 3 \
  --sc_min_similarity 0.45 \
  --sc_min_margin 0.08 \
  --enrich_schema \
  --logging_verbose \
  --document_mode all_combined \
  --input_text_dir ./datasets/intern/text/2_preprocessed \
  --output_dir ./output/all_combinedx \
  --v2_min_chunk_chars 120 \
  --v2_max_chunk_chars 2000 \
  --enable_triple_utility_filter \
  --tu_llm gpt-4.1-mini \
  --tu_prompt_template_file_path ./prompt_templates/tu_filter_template.txt \
  --tu_few_shot_example_file_path ./few_shot_examples/example/tu_few_shot_schema_level.txt
```

---

## Was macht dieser Befehl?

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| `--chunking_variant chunking2` | Adaptive Chunking (v2) | Struktur-bewusstes Splitting (Tabellen, Bullets, Prosa) |
| `--embedding_api azure` | Azure OpenAI | Embeddings über Azure statt lokaler SentenceTransformer |
| `--oie_llm gpt-4.1-mini` | GPT-4.1-mini | LLM für Tripel-Extraktion |
| `--oie_prompt_template_file_path ...oie_schema_level2.txt` | Strikter Schema-Prompt | "Precision > Recall", nur ontologie-konforme Tripel |
| `--oie_few_shot_example_file_path ...oie_few_shot_schema_level.txt` | Domain-Beispiele | LeanIX/ITAM-spezifische Few-Shot-Beispiele |
| `--sc_top_k 3` | Top-3 Kandidaten | Kanonisierung prüft 3 Schema-Relationen |
| `--sc_min_similarity 0.45` | Similarity ≥ 0.45 | Mindestähnlichkeit für Kanonisierung |
| `--sc_min_margin 0.08` | Margin ≥ 0.08 | Mindestabstand Top-1 zu Top-2 |
| `--enrich_schema` | Schema-Anreicherung | Neue Relationen werden ins Schema aufgenommen |
| `--document_mode all_combined` | Verzeichnismodus | Alle `*_combined*.txt` aus dem Inputverzeichnis |
| `--v2_min_chunk_chars 120` | Min. 120 Zeichen | Chunks unter 120 Zeichen werden zusammengeführt |
| `--v2_max_chunk_chars 2000` | Max. 2000 Zeichen | Chunks werden bei 2000 Zeichen gesplittet |
| `--enable_triple_utility_filter` | TU-Filter aktiv | LLM filtert nicht-schema-relevante Tripel heraus |

---

## Ausgabe

Nach dem Lauf enthält `./output/all_combinedx/`:

```
all_combinedx/
├── chunks_v2.jsonl              # Alle erzeugten Chunks
├── chunks_text_for_edc_v2.txt   # Chunk-Texte (ein Chunk pro Zeile)
├── run_settings.log             # Protokoll aller Laufparameter
└── iter0/
    ├── oie_kg.txt               # Roh-Tripel nach OIE
    ├── canon_kg.txt             # Kanonisierte Tripel
    ├── useful_kg.txt            # Gefilterte, nützliche Tripel
    ├── canon_kg_dedup.txt       # Deduplizierte Ausgabe
    ├── relation_definitions.json # Relationsdefinitionen
    └── result_at_each_stage.json # Zwischenergebnisse aller Pipeline-Stufen
```

---

## Varianten

### Nur Chunking testen (kein LLM-Aufruf)

```bash
python run_new.py \
  --chunking_variant chunking2 \
  --document_mode all_combined \
  --input_text_dir ./datasets/intern/text/2_preprocessed \
  --output_dir ./output/chunking_test \
  --v2_min_chunk_chars 120 \
  --v2_max_chunk_chars 2000 \
  --run_mode test
```

### Ohne Definition & Canonicalization (nur OIE + Filter)

Füge `--disable_dc` zum Quickstart-Befehl hinzu:

```bash
python run_new.py \
  ... \
  --disable_dc
```

### Evaluation nach dem Lauf

```bash
python run_evaluation.py \
  --edc_output ./output/all_combinedx/iter0/canon_kg_dedup.txt \
  --reference ./datasets/intern/gold/leanix_ontology_tripel_cleaned.txt \
  --sample_size 50 \
  --sample_seed 42 \
  --relation_threshold 0.85 \
  --entity_threshold 0.85
```
