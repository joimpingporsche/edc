# EDC Framework – Vollständige Projektdokumentation

> **EDC** = **E**xtract → **D**efine → **C**anonicalize  
> LLM-basiertes Knowledge-Graph-Konstruktionsframework für die Extraktion schemakonformer Tripel aus semi-strukturierten Dokumenten (Confluence/PDF) im Bereich Enterprise Architecture / IT Asset Management.

---

## Inhaltsverzeichnis

1. [Projektübersicht](#1-projektübersicht)
2. [Architektur & Pipeline](#2-architektur--pipeline)
3. [Installation & Umgebung](#3-installation--umgebung)
4. [Einstiegspunkte & Befehle](#4-einstiegspunkte--befehle)
   - 4.1 [run.py – Original-EDC-Pipeline (alt)](#41-runpy--original-edc-pipeline-alt)
   - 4.2 [run_new.py – Neue erweiterte Pipeline](#42-run_newpy--neue-erweiterte-pipeline)
   - 4.3 [run_evaluation.py – Evaluations-Pipeline](#43-run_evaluationpy--evaluations-pipeline)
   - 4.4 [run.sh – Shell-Beispielskript](#44-runsh--shell-beispielskript)
5. [Kernmodule (edc/)](#5-kernmodule-edc)
6. [Preprocessing](#6-preprocessing)
7. [Evaluation](#7-evaluation)
8. [Utility-Skripte](#8-utility-skripte)
9. [Prompt-Templates](#9-prompt-templates)
10. [Few-Shot-Beispiele](#10-few-shot-beispiele)
11. [Schemas & Datensätze](#11-schemas--datensätze)
12. [Design-Iterationen](#12-design-iterationen)
13. [Evaluationsergebnisse](#13-evaluationsergebnisse)
14. [Beispielbefehle](#14-beispielbefehle)

---

## 1. Projektübersicht

Das EDC-Framework extrahiert Knowledge-Graph-Tripel (`[Subjekt, Relation, Objekt]`) aus Textdokumenten mithilfe von Large Language Models (LLMs). Der dreiphasige Ansatz:

1. **Extract (OIE):** LLM extrahiert offene SPO-Tripel aus Text
2. **Define:** LLM definiert die extrahierten Relationen kontextbezogen
3. **Canonicalize:** Embedding-basierte Ähnlichkeitssuche + LLM-Verifikation mappt Relationen auf ein Zielschema

Erweitert um:
- **Triple Utility Filter:** LLM-basierte Nachfilterung auf schemakonformer Ebene
- **Adaptive Chunking:** Struktur-bewusstes Splitting von Dokumenten
- **PDF-Preprocessing:** Extraktion von Text und Tabellen aus Confluence-PDFs
- **Two-Track Evaluation:** Alignment- und Enrichment-Bewertung

### Technologie-Stack

| Komponente | Technologien |
|-----------|-------------|
| LLMs | Azure OpenAI (GPT-4.1-mini), HuggingFace (Mistral-7B) |
| Embeddings | Azure OpenAI (text-embedding-3-large), SentenceTransformers (e5-mistral) |
| PDF-Verarbeitung | pdfplumber |
| Ontologie | rdflib (TTL/OWL Parsing) |
| ML-Framework | PyTorch, LangChain |

---

## 2. Architektur & Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        Eingabe                                  │
│  PDF-Dateien ──→ pdf_to_text_and_tables.py ──→ Preprocessed Text│
│  Schema (CSV) ──→ Ziel-Ontologie                               │
│  Prompt Templates + Few-Shot Beispiele                          │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Chunking (v1 oder v2)                         │
│  v1: Fixed-Window (Satz/Zeichen)                                │
│  v2: Adaptive Section-Aware (Tabellen, Bullet-Listen, Prosa)    │
│  Ausgabe: chunks.jsonl + chunks.txt                             │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EDC Framework                                │
│                                                                 │
│  ① OIE (extract.py)                                            │
│     └─→ Roh-Tripel [Subjekt, Relation, Objekt]                 │
│                                                                 │
│  ② Schema Definition (schema_definition.py)                     │
│     └─→ Relation → Definition (natürlichsprachlich)            │
│                                                                 │
│  ③ Schema Canonicalization (schema_canonicalization.py)          │
│     ├─ Embedding-Retrieval: Top-k ähnliche Schema-Relationen   │
│     ├─ Confidence Gate: Similarity + Margin Thresholds          │
│     └─ LLM-Verifikation: Bestätigung der Zuordnung             │
│                                                                 │
│  ④ Triple Utility Filter (triple_utility_filter.py) [optional]  │
│     └─→ Nur schema-relevante Tripel behalten                   │
│                                                                 │
│  ⑤ Iterative Refinement [optional]                              │
│     ├─ Entity Extraction (entity_extraction.py)                 │
│     ├─ Schema Retrieval (schema_retriever.py)                   │
│     └─→ Hints für nächste OIE-Iteration                        │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ausgabe                                    │
│  canon_kg.txt / useful_kg.txt / canon_kg_dedup.txt              │
│  result_at_each_stage.json (Zwischenergebnisse)                 │
│  relation_definitions.json                                      │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Evaluation                                   │
│  Deduplizierung → Two-Track Evaluation → LLM Labeling          │
│  Track 1: Alignment vs. Gold-Ontologie                          │
│  Track 2: Enrichment (Neuartige, nützliche Tripel)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Installation & Umgebung

### Linux/CUDA (GPU-Unterstützung)

```bash
conda env create -f environment.yml
conda activate edc
```

Enthält: PyTorch + CUDA 12.1, xformers, AWS SDKs, vollständige GPU-Unterstützung.

### macOS (Lokale Entwicklung)

```bash
conda env create -f mac_environment.yml
conda activate edc
```

Enthält: PyTorch (CPU/MPS), kein CUDA, reduzierte Abhängigkeiten.

### Umgebungsvariablen

Für Azure OpenAI Modelle müssen folgende Umgebungsvariablen gesetzt sein:

```bash
export AZURE_OPENAI_ENDPOINT="https://<endpoint>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<api-key>"
export AZURE_OPENAI_API_VERSION="2024-02-01"
```

---

## 4. Einstiegspunkte & Befehle

### 4.1 `run.py` – Original-EDC-Pipeline (alt)

> **Hinweis:** Dies ist das **originale, unveränderte Skript** aus dem EDC-Paper. Es dient als Referenzimplementierung und wird für die internen Experimente **nicht mehr aktiv verwendet**. Stattdessen wird [`run_new.py`](#42-run_newpy--neue-erweiterte-pipeline) eingesetzt.

Originaler EDC-Runner aus dem Forschungspaper. Verarbeitet eine einzelne Textdatei (eine Zeile = ein Text). Enthält kein Chunking, kein Dokument-Loading aus Verzeichnissen und kein Run-Logging.

#### Alle Argumente

**OIE (Open Information Extraction):**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--oie_llm` | str | `mistralai/Mistral-7B-Instruct-v0.2` | LLM für die Tripel-Extraktion |
| `--oie_prompt_template_file_path` | str | `./prompt_templates/oie_template.txt` | Prompt-Template für OIE |
| `--oie_few_shot_example_file_path` | str | `./few_shot_examples/example/oie_few_shot_examples.txt` | Few-Shot-Beispiele für OIE |

**Schema Definition:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--sd_llm` | str | `mistralai/Mistral-7B-Instruct-v0.2` | LLM für Schema-Definition |
| `--sd_prompt_template_file_path` | str | `./prompt_templates/sd_template.txt` | Prompt-Template für Schema-Definition |
| `--sd_few_shot_example_file_path` | str | `./few_shot_examples/example/sd_few_shot_examples.txt` | Few-Shot-Beispiele für Schema-Definition |

**Schema Canonicalization:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--sc_llm` | str | `mistralai/Mistral-7B-Instruct-v0.2` | LLM für Kanonisierungs-Verifikation |
| `--sc_embedder` | str | `intfloat/e5-mistral-7b-instruct` | Embedding-Modell für Ähnlichkeitssuche |
| `--sc_prompt_template_file_path` | str | `./prompt_templates/sc_template.txt` | Prompt-Template für Kanonisierung |
| `--sc_top_k` | int | `3` | Anzahl Schema-Kandidaten vor LLM-Verifikation |
| `--sc_min_similarity` | float | `None` | Minimale Ähnlichkeit für Kanonisierung |
| `--sc_min_margin` | float | `None` | Mindestabstand zwischen Top-1 und Top-2 Kandidat |
| `--embedding_api` | str | `local` | Embedding-Backend: `local` (SentenceTransformer) oder `azure` (Azure OpenAI) |
| `--azure_openai_api_version` | str | `None` | Azure OpenAI API Version (Fallback: Umgebungsvariable) |

**Refinement:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--refinement_iterations` | int | `0` | Anzahl Verfeinerungsiterationen |
| `--sr_adapter_path` | str | `None` | Pfad zu fine-tuned Adapter des Schema Retrievers |
| `--sr_embedder` | str | `intfloat/e5-mistral-7b-instruct` | Embedding-Modell für Schema Retriever |
| `--oie_refine_prompt_template_file_path` | str | `./prompt_templates/oie_r_template.txt` | Prompt-Template für verfeinerte OIE |
| `--oie_refine_few_shot_example_file_path` | str | `./few_shot_examples/example/oie_few_shot_refine_examples.txt` | Few-Shot-Beispiele für verfeinerte OIE |

**Entity Extraction:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--ee_llm` | str | `mistralai/Mistral-7B-Instruct-v0.2` | LLM für Entity-Extraktion |
| `--ee_prompt_template_file_path` | str | `./prompt_templates/ee_template.txt` | Prompt-Template für Entity-Extraktion |
| `--ee_few_shot_example_file_path` | str | `./few_shot_examples/example/ee_few_shot_examples.txt` | Few-Shot-Beispiele für Entity-Extraktion |
| `--em_prompt_template_file_path` | str | `./prompt_templates/em_template.txt` | Prompt-Template für Entity-Merging |

**Triple Utility Filter:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--enable_triple_utility_filter` | Flag | `False` | Triple Utility Filter aktivieren |
| `--tu_llm` | str | `mistralai/Mistral-7B-Instruct-v0.2` | LLM für Triple-Filterung |
| `--tu_prompt_template_file_path` | str | `./prompt_templates/tu_filter_template.txt` | Prompt-Template für Triple-Filter |
| `--tu_few_shot_example_file_path` | str | `None` | Few-Shot-Beispiele für Triple-Filter |

**Eingabe/Ausgabe:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--run_dc` | str | `"true"` | `"false"` → Schema Definition & Canonicalization überspringen |
| `--input_text_file_path` | str | `./datasets/example.txt` | Eingabe-Textdatei (ein Text pro Zeile) |
| `--target_schema_path` | str | `./schemas/example_schema.csv` | CSV mit Zielschema (Relation → Definition) |
| `--enrich_schema` | Flag | `False` | Nicht-kanonisierbare Relationen zum Schema hinzufügen |
| `--output_dir` | str | `./output/tmp` | Ausgabeverzeichnis |
| `--logging_verbose` | Flag | – | Logging auf INFO setzen |
| `--logging_debug` | Flag | – | Logging auf DEBUG setzen |

---

### 4.2 `run_new.py` – Neue erweiterte Pipeline

> **Dies ist der aktive, empfohlene Einstiegspunkt** für alle Experimente und Produktionsläufe.

Neues, eigens entwickeltes Skript, das `run.py` ersetzt und um folgende Funktionen erweitert:
- **Dokument-Loading:** Einzeldatei oder ganzes Verzeichnis (`--document_mode`)
- **Integriertes Chunking:** Baseline (v1) und adaptives Section-Chunking (v2)
- **Run-Logging:** Automatische Protokollierung aller Laufparameter
- **Test-Modus:** Chunking isoliert testen ohne EDC-Ausführung (`--run_mode test`)
- **Disable D+C:** Definition & Canonicalization überspringen (`--disable_dc`)

#### Zusätzliche/Geänderte Argumente (über run.py hinaus)

**Laufmodus:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--run_mode` | str | `normal` | `test` → nur Chunking ausführen, kein EDC |
| `--disable_dc` | Flag | `False` | Schema Definition & Canonicalization überspringen (nur OIE + Refinement) |
| `--document_mode` | str | `test` | `test` = einzelne Datei, `all_combined` = Verzeichnis mit Pattern-Matching |

**Dokument-Eingabe:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--input_text_file_path` | str | `None` | Einzelne Eingabedatei (exklusiv mit `--input_text_dir`) |
| `--input_text_dir` | str | `None` | Verzeichnis mit `.txt`-Dateien (exklusiv mit `--input_text_file_path`) |

**Chunking-Strategie:**

| Argument | Typ | Default | Choices | Beschreibung |
|----------|-----|---------|---------|-------------|
| `--chunking_variant` | str | `v1` | `v1`, `v2`, `chunking1`, `chunking2`, `1`, `2`, `baseline`, `adaptive` | Chunking-Strategie auswählen |

**V1 Baseline Chunking (Fixed-Window):**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--v1_mode` | str | `sentence` | Modus: `sentence` oder `char` |
| `--v1_window_sentences` | int | `4` | Satzfenstergröße |
| `--v1_overlap_sentences` | int | `1` | Satzüberlappung |
| `--v1_window_chars` | int | `1800` | Zeichenfenstergröße |
| `--v1_overlap_chars` | int | `300` | Zeichenüberlappung |

**V2 Adaptive Section Chunking:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--v2_max_chunk_chars` | int | `2200` | Maximale Chunk-Größe in Zeichen |
| `--v2_min_chunk_chars` | int | `120` | Minimale Chunk-Größe in Zeichen |
| `--v2_bullet_group_size` | int | `6` | Aufzählungspunkte pro Chunk |
| `--v2_prose_window_sentences` | int | `4` | Satzfenster für Fließtext |
| `--v2_prose_overlap_sentences` | int | `1` | Satzüberlappung für Fließtext |
| `--v2_table_rows_per_chunk` | int | `25` | Tabellenzeilen pro Chunk |

**Ausgabe:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--output_dir` | str | `./output/tmp_chunked` | Ausgabeverzeichnis |

#### Ablauf von run_new.py

1. Argumente parsen
2. Dokumente laden (Einzeldatei oder Verzeichnis)
3. Chunking-Strategie anwenden (v1 oder v2)
4. Chunk-Ausgaben schreiben (JSONL + TXT)
5. Falls `run_mode != test`: EDC-Framework initialisieren und Pipeline ausführen
6. Run-Settings-Log mit Metadaten schreiben

---

### 4.3 `run_evaluation.py` – Evaluations-Pipeline

Automatisierte Evaluation: Deduplizierung → Evaluation Pass 1 → LLM-Labeling → Evaluation Pass 2.

#### Alle Argumente

**Pflichtargumente:**

| Argument | Typ | Beschreibung |
|----------|-----|-------------|
| `--edc_output` | str | Pfad zur KG-Ausgabedatei (z.B. `useful_kg.txt`) |
| `--reference` | str | Pfad zur Gold-Ontologie (z.B. `leanix_ontology_tripel_cleaned.txt`) |

**Optionale Pfade:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--alignment_json` | str | `None` | Relation-Alignment JSON (vorab berechnet) |
| `--result_at_each_stage_json` | str | `None` | Zwischenergebnis-JSON für Chunk-Kontext |
| `--output_dir` | str | `None` | Ausgabeverzeichnis (Default: Elternverzeichnis von `--edc_output`) |

**LLM & Anfragen:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--llm` | str | `gpt-4.1-mini` | Azure OpenAI Deployment für LLM-Labeling |
| `--request_delay` | float | `0.3` | Pause in Sekunden zwischen LLM-Anfragen |

**Evaluationsparameter:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--relation_threshold` | float | `0.85` | Semantischer Schwellenwert für Relationsmatching |
| `--entity_threshold` | float | `0.85` | Semantischer/Fuzzy-Schwellenwert für Entity-Matching |
| `--sample_size` | int | `100` | Anzahl neuartiger Tripel für manuelle Überprüfung |
| `--sample_seed` | int | `42` | Deterministischer Seed für stratifiziertes Sampling |

**Deduplizierung:**

| Argument | Typ | Default | Choices | Beschreibung |
|----------|-----|---------|---------|-------------|
| `--dedup_scope` | str | `global` | `line`, `global` | Scope: `global` = dateiübergreifend |
| `--skip_dedup` | Flag | `False` | – | Deduplizierung überspringen |

#### Generierte Ausgaben

| Datei | Beschreibung |
|-------|-------------|
| `dedup_output.txt` | Deduplizierte Tripel |
| `novel_sample_for_manual_review.csv` | Stichprobe für manuelle Überprüfung |
| `ai_eval.csv` | LLM-Labels (SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED) |
| `eval_report_pass1.json` | Erster Evaluationsbericht |
| `eval_report_final.json` | Finaler Bericht mit LLM-Labels |

#### Ablauf der Evaluation

```
edc_output (useful_kg.txt)
    │
    ▼
[1] Deduplizierung (deduplicate_triples.py)
    │   → dedup_output.txt
    ▼
[2] Evaluation Pass 1 (two_track_evaluation.py)
    │   → eval_report_pass1.json
    │   → novel_sample_for_manual_review.csv
    ▼
[3] LLM-Labeling (Azure OpenAI)
    │   → ai_eval.csv
    ▼
[4] Evaluation Pass 2 (two_track_evaluation.py + Labels)
        → eval_report_final.json
```

---

### 4.4 `run.sh` – Shell-Beispielskript

Beispielkonfiguration mit Mistral-Modellen für den Example-Datensatz:

```bash
OIE_LLM=mistralai/Mistral-7B-Instruct-v0.2
SD_LLM=mistralai/Mistral-7B-Instruct-v0.2
SC_LLM=mistralai/Mistral-7B-Instruct-v0.2
SC_EMBEDDER=intfloat/e5-mistral-7b-instruct
DATASET=example
```

---

## 5. Kernmodule (edc/)

### `edc/edc_framework.py` – Hauptorchestrierung

Die zentrale `EDC`-Klasse steuert die gesamte Pipeline.

| Methode | Zweck |
|---------|-------|
| `load_model(model_name, model_type)` | Modell laden (HuggingFace LLM oder Embedder) mit Caching |
| `oie(input_text_list, previous_extracted_triplets_list)` | OIE-Extraktion (normal oder verfeinert mit Hints) |
| `schema_definition(input_text_list, oie_triplets_list)` | Schema-Definition für extrahierte Relationen |
| `schema_canonicalization(...)` | Schema-Kanonisierung mit Embedding-Retrieval + LLM |
| `construct_refinement_hint(...)` | Refinement-Hints konstruieren (Entities + Schema) |
| `triple_utility_filter(triplets_list)` | Tripel-Filterung auf Schema-Nützlichkeit |
| `extract_kg(input_text_list, output_dir, refinement_iterations)` | **Hauptmethode:** Gesamte Pipeline ausführen |

### `edc/extract.py` – Open Information Extraction

Die `Extractor`-Klasse extrahiert SPO-Tripel aus Text mittels LLM. Unterstützt:
- Reguläre Extraktion (Prompt + Few-Shot)
- Verfeinerte Extraktion mit Entity- und Relations-Hints

### `edc/schema_definition.py` – Schema-Definition

Die `SchemaDefiner`-Klasse lässt das LLM extrahierte Relationen natürlichsprachlich definieren. Erstellt ein Dictionary `Relationsname → Definition`.

### `edc/schema_canonicalization.py` – Schema-Kanonisierung

Die `SchemaCanonicalizer`-Klasse mappt extrahierte Relationen auf das Zielschema:

1. Relation bereits im Schema → direkt übernehmen
2. Embedding-basierte Top-k Ähnlichkeitssuche
3. Confidence Gate prüfen (Similarity + Margin Thresholds)
4. LLM-Verifikation der Zuordnung
5. Bei Misserfolg: Optional ins Schema aufnehmen (`enrich_schema`)

### `edc/schema_retriever.py` – Schema Retriever

Ruft relevante Schema-Relationen für Refinement-Hints ab. Verwendet Embeddings zur Ähnlichkeitssuche zwischen Input-Text und Schema-Relationen.

### `edc/entity_extraction.py` – Entity-Extraktion

Extrahiert und verschmilzt Entitäten für die Refinement-Phase:
- `extract_entities()`: LLM identifiziert Entitäten im Text
- `merge_entities()`: LLM verschmilzt zwei Entitätslisten (Duplikate/Varianten)

### `edc/triple_utility_filter.py` – Triple Utility Filter

**Neues Modul (nicht im Original-EDC).** LLM-basierte Nachfilterung:
- Klassifiziert Tripel als schema-relevant oder nicht
- Abstrahiert Instanz-Entitäten zu generischen Typen
- Mappt Relationen auf eine Whitelist (31 Prädikate)
- Fallback auf ungefilterte Tripel bei Parsing-Fehlern

---

## 6. Preprocessing

### `edc/preprocessing/pdf_to_text_and_tables.py` – PDF-Extraktion

Extrahiert Text und strukturierte Tabellen aus PDF-Dokumenten (Confluence-PDFs).

**Argumente:**

| Argument | Typ | Beschreibung |
|----------|-----|-------------|
| `pdf_path` | positional | Pfad zur PDF-Eingabedatei |
| `--output_dir` | str | Ausgabeverzeichnis |

**Erzeugt pro Dokument:**
- `*_combined.txt` – Kombinierter Text mit Sektionsmarkern und Tabellen-JSON
- `*_plain_text.txt` – Nur Fließtext
- `*_tables.jsonl` – Extrahierte Tabellen als JSON Lines

**Funktionen:**
- `clean_cell()` – Whitespace normalisieren
- `normalize_headers()` – Spaltenheader standardisieren
- `fix_spaced_word()` – PDF-Artefakte reparieren (z.B. "O bjective" → "Objective")
- `fill_down_merged_cells()` – Verbundene Tabellenzellen auffüllen
- `process_table()` – Tabellen in strukturierte Zeilen umwandeln
- `group_words_to_lines()` – Wortliste in physische Textzeilen konvertieren

### `edc/preprocessing/chunking_v1.py` – Baseline Chunking

Fixed-Window-Chunking mit zwei Modi:

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `mode` | `sentence` | `sentence` oder `char` |
| `window_sentences` | `4` | Satzfenstergröße |
| `overlap_sentences` | `1` | Satzüberlappung |
| `window_chars` | `1800` | Zeichenfenstergröße |
| `overlap_chars` | `300` | Zeichenüberlappung |

**Chunk-Typ:** Immer `window_text`.

### `edc/preprocessing/chunking_v2.py` – Adaptive Section Chunking

Strukturbewusstes Chunking mit Erkennung von Sektionen, Tabellen und Bullet-Listen.

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `max_chunk_chars` | `2200` | Maximale Chunk-Größe |
| `min_chunk_chars` | `120` | Minimale Chunk-Größe |
| `bullet_group_size` | `6` | Aufzählungspunkte pro Chunk |
| `prose_window_sentences` | `4` | Satzfenster für Prosa |
| `prose_overlap_sentences` | `1` | Satzüberlappung für Prosa |
| `table_rows_per_chunk` | `25` | Tabellenzeilen pro Chunk |

**Chunk-Typen:** `table_json`, `table_rows`, `section_bullets`, `section_prose`

**Logik:**
1. Sektionen parsen (`[SECTION_START]`/`[SECTION_END]` Marker)
2. Inhaltstyp erkennen (Tabelle, Bullet-Liste, Fließtext)
3. Typspezifisches Chunking anwenden
4. Sehr kurze Chunks mit Nachbarn verschmelzen
5. Sektionstitel als Kontext-Prefix hinzufügen

---

## 7. Evaluation

### `evaluate/two_track_evaluation.py` – Two-Track Evaluation

Zweispuriges Evaluationsframework:

**Track 1: Alignment** – Vergleich mit Gold-Ontologie
- Precision, Recall, F1
- Exaktes und normalisiertes Matching
- Coverage-Metriken

**Track 2: Enrichment** – Neuartige/nützliche Tripel
- Novelty Rate
- Stratifiziertes Sampling
- LLM-Labels: `SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED`
- Enrichment Precision

**Alle Argumente:**

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--edc_output` | str | **erforderlich** | Pfad zur EDC-Vorhersagedatei |
| `--reference` | str | **erforderlich** | Pfad zur Gold-Ontologie |
| `--alignment_json` | str | `None` | Relation-Alignment JSON |
| `--result_at_each_stage_json` | str | `None` | Kontextdatei für Review-Exporte |
| `--save_json` | str | **erforderlich** | Ausgabe-Report JSON |
| `--review_sample_output` | str | – | CSV für Manual-Review-Stichprobe |
| `--alignment_matches_csv` | str | – | CSV für Alignment-Matches |
| `--top_predicates_csv` | str | – | CSV für Top-Prädikate |
| `--relation_threshold` | float | `0.85` | Schwellenwert Relationsmatching |
| `--entity_threshold` | float | `0.85` | Schwellenwert Entity-Matching |
| `--sample_size` | int | `100` | Stichprobengröße neuartiger Tripel |
| `--sample_seed` | int | `42` | Seed für stratifiziertes Sampling |
| `--labels_input` | str | `None` | Gelabelte Review-CSV für Enrichment |
| `--max_invalid_examples` | int | `50` | Max. Beispiele für Error-Breakdown |

### `evaluate/deduplicate_triples.py` – Deduplizierung

Entfernt doppelte Tripel aus EDC-Ausgaben.

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--input` | str | **erforderlich** | Eingabedatei (z.B. `canon_kg.txt`) |
| `--output` | str | **erforderlich** | Ausgabedatei |
| `--scope` | str | `global` | `line` = innerhalb einer Zeile, `global` = dateiübergreifend |
| `--keep_empty_lines` | Flag | `False` | Leerzeilen beibehalten |

### `evaluate/evaluation_script.py` – Legacy-Evaluation

Älteres Evaluationsskript mit NER-ähnlicher Evaluation (XML-Konvertierung, WebNLG-Metriken). Verwendet nervaluate für Precision/Recall/F1.

### `evaluate/evaluate_ontology_compliance.py` – Kompatibilitäts-Wrapper

Leitet Aufrufe an `two_track_evaluation.py` weiter.

---

## 8. Utility-Skripte

### `edc/utils/llm_utils.py` – LLM & Embedding Utilities

| Funktion/Klasse | Beschreibung |
|------------------|-------------|
| `AzureEmbeddingModel` | SentenceTransformer-kompatibeler Adapter für Azure OpenAI Embeddings |
| `free_model()` | Modell auf CPU verschieben, GPU-Cache leeren |
| `get_embedding_e5mistral()` | Embeddings mit E5-Mistral generieren |
| `get_embedding_sts()` | Embeddings mit SentenceTransformer generieren |
| `parse_raw_triplets()` | LLM-Ausgabe in Tripel-Liste parsen (Bracket-Matching) |
| `parse_raw_entities()` | LLM-Ausgabe in Entity-Liste parsen |
| `parse_relation_definition()` | LLM-Ausgabe in Relation-Definition-Dict parsen |
| `is_model_openai()` | Prüfen ob Modellname ein OpenAI-Modell ist |
| `generate_completion_transformers()` | Completion mit HuggingFace-Modell generieren |
| `openai_chat_completion()` | Completion mit Azure OpenAI generieren |

### `edc/utils/align_relation_definitions.py` – Relation-Alignment

Semantisches Alignment extrahierter Relationsdefinitionen zu Gold-Referenzen.

| Argument | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `--system` | str | `output/all_combined4/iter0/relation_definitions.json` | System-Relationsdefinitionen |
| `--gold` | str | `datasets/intern/gold/leanix_relation_definitions_from_ttl.json` | Gold-Relationsdefinitionen |
| `--output` | str | `output/all_combined4/relation_definition_alignment.json` | Ausgabe-JSON |
| `--embedding_backend` | str | `sentence_transformers` | `sentence_transformers` oder `azure_openai` |
| `--model` | str | `sentence-transformers/all-MiniLM-L6-v2` | SentenceTransformer Modellname |
| `--azure_deployment` | str | `None` | Azure OpenAI Deployment |
| `--azure_api_version` | str | `None` | Azure OpenAI API Version |
| `--top_k` | int | `3` | Top-k Kandidaten pro Relation |
| `--min_similarity` | float | `0.7` | Minimaler Ähnlichkeitsschwellenwert |
| `--min_margin` | float | `0.03` | Minimaler Abstand Top-1 zu Top-2 |
| `--definition_only` | Flag | `False` | Nur Definitionen verwenden (ohne Relationsnamen) |

### `edc/utils/ttl_to_gold_txt.py` – TTL → Gold-Text Konverter

Konvertiert RDF Turtle Ontologiedateien in EDC-kompatibles Textformat.

| Argument | Typ | Beschreibung |
|----------|-----|-------------|
| `--input_ttl` | str | **erforderlich** – Pfad zur `.ttl` Datei |
| `--output_txt` | str | **erforderlich** – Pfad zur Ausgabe `.txt` |
| `--class_mapping_jsonl` | str | Optional: JSONL mit Klassen-URI→Name Mapping |
| `--include_subclass` | Flag | `subClassOf`-Tripel einbeziehen |
| `--one_line` | Flag | Alle Tripel in eine Zeile (Default: ein Tripel pro Zeile) |

### `edc/utils/extract_gold_relation_comments.py`

Extrahiert Relationsdefinitionen aus `rdfs:comment`-Feldern in TTL-Ontologie-ObjectProperty-Einträgen.

### `edc/utils/extract_relation_definitions.py`

Extrahiert Relationsdefinitionen aus `result_at_each_stage.json`, dedupliziert (behält längste) und gibt sortiertes JSON-Dict aus.

### `edc/utils/collect_schema_retrieval_data.py`

Sammelt Relationsdefinitionen aus `result_at_each_stage.json` für Training/Analyse.

### `edc/utils/run_pdf_batch.py`

Batch-Runner: Ruft `pdf_to_text_and_tables.py` für alle PDFs in `datasets/intern/pdfs/` auf.

### `edc/utils/e5_mistral_utils.py`

Fine-Tuning-Utilities für E5-Mistral Embeddings mit LoRA + InfoNCE-Loss (kontrastives Lernen).

---

## 9. Prompt-Templates

Alle Templates befinden sich in `prompt_templates/`:

| Datei | Verwendung | Phase |
|-------|-----------|-------|
| `oie_template.txt` | Basis-OIE Extraktion | Extract (Iteration 1) |
| `oie_schema_level1.txt` | Schema-Level OIE (moderater Fokus) | Extract (Iteration 2–3) |
| `oie_schema_level2.txt` | Schema-Level OIE (strikt, Precision > Recall) | Extract (Iteration 4) |
| `oie_r_template.txt` | Verfeinerte OIE mit Entity/Relation-Hints | Refinement |
| `sd_template.txt` | Schema-Definition | Define |
| `sc_template.txt` | Schema-Kanonisierungs-Verifikation | Canonicalize |
| `ee_template.txt` | Entity-Extraktion | Refinement |
| `em_template.txt` | Entity-Merging | Refinement |
| `tu_filter_template.txt` | Triple Utility Filter | Filter |

### Prompt-Versionen im Detail

**OIE v0 (`oie_template.txt`):** Generische SPO-Extraktion ohne Schema-Constraints. Extrahiert beliebige Tripel aus dem Text.

**OIE v1 (`oie_schema_level1.txt`):** Schema-Level-Fokus: Nur `[TypOderKonzept1, Relation, TypOderKonzept2]`. Keine Instanzen, keine spezifischen Tool-/Organisationsnamen.

**OIE v2 (`oie_schema_level2.txt`):** Strengster Prompt: "Prefer precision over recall". Ausschluss temporaler Status-/Rollendetails. Erfordert: (1) stabile Relation, (2) Ontologie-Wert, (3) Textbeleg. Bei Unsicherheit → leere Liste.

---

## 10. Few-Shot-Beispiele

Alle Beispiele befinden sich in `few_shot_examples/example/`:

| Datei | Verwendung | Format |
|-------|-----------|--------|
| `oie_few_shot_examples.txt` | Basis-OIE (WebNLG-Stil) | `Text: ...\nTriplets: [['Subj', 'rel', 'Obj']]` |
| `oie_few_shot_schema_level.txt` | Schema-Level OIE (LeanIX-Domäne) | Konzept-Level, CamelCase |
| `oie_few_shot_refine_examples.txt` | Verfeinerte OIE | Wie schema_level + Hints |
| `sd_few_shot_examples.txt` | Schema-Definition | Relation → natürlichsprachliche Definition |
| `ee_few_shot_examples.txt` | Entity-Extraktion | NER-Stil mit Entitätslisten |
| `tu_few_shot_schema_level.txt` | Triple Utility Filter | Instanz→Typ Abstraktion + Whitelist-Mapping |

**Beispiel `oie_few_shot_schema_level.txt`:**
```
Text: A Digital Solution is a cohesive construct that delivers business value
by integrating multiple IT Products.
Triplets: [['Digital_Solution', 'delivers', 'Business_Value'],
           ['Digital_Solution', 'integrates', 'IT_Product']]
```

---

## 11. Schemas & Datensätze

### Schemas (`schemas/`)

| Datei | Beschreibung |
|-------|-------------|
| `example_schema.csv` | Beispiel-Domänenschema |
| `rebel_schema.csv` | WebNLG REBEL-Schema |
| `webnlg_schema.csv` | WebNLG-Schema |
| `wiki-nre_schema.csv` | Wiki-NRE-Schema |

**Format:** CSV mit Spalten `Relation, Definition`.

### Datensätze (`datasets/`)

| Pfad | Beschreibung |
|------|-------------|
| `datasets/extern/` | Externe Referenzdatensätze |
| `datasets/intern/pdfs/` | 22 LeanIX Confluence PDFs (interner Datensatz) |
| `datasets/intern/text/1_raw_text/` | Rohtext-Extraktion aus PDFs |
| `datasets/intern/text/2_preprocessed/` | Vorverarbeitete Textausgaben |
| `datasets/intern/gold/leanix_ontology_tripel_cleaned.txt` | **Gold-Standard** (936 Tripel, 30 Prädikate) |
| `datasets/intern/gold/leanix_ontology_cleaned.ttl` | LeanIX Ontologie als Turtle-Datei |
| `datasets/intern/gold/leanix_ontology_classes.jsonl` | Klassen-URI→Name Mapping |

---

## 12. Design-Iterationen

Das Projekt folgt einem Design-Science-Ansatz mit 4 Iterationen:

| Iteration | Output-Dir | OIE Prompt | disable_dc | TU Filter | Kernänderung |
|-----------|-----------|-----------|-----------|-----------|-------------|
| **1 (Baseline)** | `all_combined2` | `oie_template.txt` | Nein | Nein | Original-EDC Prompts |
| **2** | `all_combined4` | `oie_schema_level1.txt` | Nein | Nein | Schema-Level OIE Prompt v1 |
| **3** | `all_combined5` | `oie_schema_level1.txt` | Ja | Ja | Triple Utility Filter aktiviert |
| **4 (Final)** | `all_combined_prompt2_with_filter` | `oie_schema_level2.txt` | Ja | Ja | Strikterer OIE Prompt v2 |

### Chunking-Parameter (Iteration 1–4)

| Parameter | Iter 1 | Iter 2–4 |
|-----------|--------|----------|
| `v2_max_chunk_chars` | 1500 | 2000 |
| `v2_min_chunk_chars` | 120 | 120 |
| `v2_prose_window_sentences` | 4 | 4 |
| `v2_table_rows_per_chunk` | 25 | 25 |
| `v2_bullet_group_size` | 6 | 6 |

Ergebnis: **409 Chunks** über alle Iterationen (identisch ab Iter 2).

---

## 13. Evaluationsergebnisse

### Kernergebnisse (Iteration 1 → 4)

| Metrik | Iter 1 | Iter 2 | Iter 3 | Iter 4 | Trend |
|--------|--------|--------|--------|--------|-------|
| `prediction_total` | 2472 | 1509 | 1160 | 516 | ↓ Fokussierung |
| `unique_predicates_total` | 674 | 379 | 110 | 65 | ↓ Schema-Konformität |
| `unknown_relation (invalid)` | 2262 | 1299 | 212 | 101 | ↓ Ontologie-konform |
| `relation_valid_rate` | 0.085 | 0.139 | 0.817 | 0.804 | ↑ Sprung bei Iter 3 |
| `domain_valid_rate` | 0.009 | 0.023 | 0.163 | 0.238 | ↑ |
| `range_valid_rate` | 0.009 | 0.013 | 0.078 | 0.134 | ↑ |
| `enrichment_precision` | 0.66 | 0.52 | 0.28 | 0.40 | V-Form |
| `alignment_F1` | 0.031 | 0.025 | 0.065 | 0.060 | Peak bei Iter 3 |

### Kausale Kette

1. **Iter 1→2:** Prompt-Verfeinerung allein → minimaler Gewinn (8.5% → 13.9% relation_valid_rate)
2. **Iter 2→3:** **Triple Utility Filter aktiviert** → massiver Gewinn (13.9% → 81.7%), aber Enrichment sinkt (0.52 → 0.28)
3. **Iter 3→4:** Strikterer OIE Prompt v2 → Stabilisierung, Enrichment-Erholung (28% → 40%)

### Erfolgszielerf (Objectives of a Solution)

Alle **MUST**-Kriterien bei Iteration 4 erfüllt:

| Kriterium | Schwellenwert | Iter 4 Wert | Status |
|-----------|-------------|-------------|--------|
| Relation Validity | ≥ 0.80 | 0.804 | ✅ |
| Unknown Relations | ≤ 101 | 101 | ✅ |
| Domain Valid Rate | ≥ 0.20 | 0.238 | ✅ |
| Range Valid Rate | ≥ 0.13 | 0.134 | ✅ |
| Normalized Exact Precision | ≥ 0.058 | erfüllt | ✅ |
| Alignment F1 | ≥ 0.059 | 0.060 | ✅ |
| Enrichment Precision | ≥ 0.40 | 0.40 | ✅ |
| Unique Predicates | ≤ 65 | 65 | ✅ |

---

## 14. Beispielbefehle

### Basis-Extraktion mit Azure OpenAI

```bash
python run_new.py \
  --chunking_variant chunking2 \
  --embedding_api azure \
  --oie_llm gpt-4.1-mini \
  --oie_few_shot_example_file_path ./few_shot_examples/example/oie_few_shot_examples.txt \
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
  --output_dir ./output/all_combined3 \
  --v2_min_chunk_chars 120 \
  --v2_max_chunk_chars 2000 \
  --run_mode test
```

### Schema-Level OIE mit Triple Utility Filter

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
  --tu_few_shot_example_file_path ./few_shot_examples/example/tu_few_shot_schema_level.txt \
  --disable_dc
```

### Evaluation mit LLM-Labeling

```bash
python evaluate/evaluate_ontology_compliance.py \
  --edc_output output/all_combined2/iter0/canon_kg_dedup.txt \
  --reference datasets/intern/gold/leanix_ontology_tripel_cleaned.txt \
  --alignment_json output/all_combined4/relation_definition_alignment_2.json \
  --result_at_each_stage_json output/all_combined2/iter0/result_at_each_stage.json \
  --sample_size 50 \
  --sample_seed 7 \
  --relation_threshold 0.85 \
  --labels_input output/all_combined2/ai_eval.csv \
  --entity_threshold 0.85 \
  --save_json output/all_combined2/two_track_eval_report_with_labels.json
```

### PDF-Vorverarbeitung

```bash
python edc/preprocessing/pdf_to_text_and_tables.py \
  datasets/intern/pdfs/Subscription+Roles+in+LeanIX\[35\].pdf \
  --output_dir datasets/intern/text/1_raw_text/subscription
```

### TTL → Gold-Text Konvertierung

```bash
python edc/utils/ttl_to_gold_txt.py \
  --input_ttl datasets/intern/gold/leanix_ontology_cleaned.ttl \
  --output_txt datasets/intern/gold/leanix_ontology_triple.txt \
  --class_mapping_jsonl datasets/intern/gold/leanix_ontology_classes.jsonl
```

### Chunking testen (ohne EDC)

```bash
python run_new.py \
  --chunking_variant chunking2 \
  --document_mode test \
  --input_text_file_path ./input_text_example.txt \
  --output_dir ./output/chunking_test \
  --v2_max_chunk_chars 2000 \
  --v2_min_chunk_chars 120 \
  --run_mode test
```

### Tripel deduplizieren

```bash
python evaluate/deduplicate_triples.py \
  --input output/all_combined2/iter0/canon_kg.txt \
  --output output/all_combined2/iter0/canon_kg_dedup.txt \
  --scope global
```

### Relation-Alignment berechnen

```bash
python edc/utils/align_relation_definitions.py \
  --system output/all_combined4/iter0/relation_definitions.json \
  --gold datasets/intern/gold/leanix_relation_definitions_from_ttl.json \
  --output output/all_combined4/relation_definition_alignment.json \
  --embedding_backend azure_openai \
  --top_k 3 \
  --min_similarity 0.7 \
  --min_margin 0.03
```

---

## Dateistruktur – Schnellreferenz

```
edc/
├── run.py                          # Basis-Pipeline Runner
├── run_new.py                      # Erweiterter Pipeline Runner (empfohlen)
├── run_evaluation.py               # Evaluations-Pipeline
├── run.sh                          # Shell-Beispielskript
│
├── edc/                            # Kernframework
│   ├── edc_framework.py            # Hauptorchestrierung (EDC-Klasse)
│   ├── extract.py                  # Open Information Extraction
│   ├── schema_definition.py        # Schema-Definition
│   ├── schema_canonicalization.py  # Schema-Kanonisierung
│   ├── schema_retriever.py         # Schema Retriever (Refinement)
│   ├── entity_extraction.py        # Entity-Extraktion (Refinement)
│   ├── triple_utility_filter.py    # Triple Utility Filter
│   ├── preprocessing/
│   │   ├── pdf_to_text_and_tables.py  # PDF → Text+Tabellen
│   │   ├── chunking_v1.py             # Baseline Chunking
│   │   └── chunking_v2.py             # Adaptive Chunking
│   ├── utils/
│   │   ├── llm_utils.py               # LLM & Embedding Utilities
│   │   ├── align_relation_definitions.py # Relation-Alignment
│   │   ├── ttl_to_gold_txt.py         # TTL → Text Konverter
│   │   ├── extract_gold_relation_comments.py
│   │   ├── extract_relation_definitions.py
│   │   ├── collect_schema_retrieval_data.py
│   │   ├── run_pdf_batch.py           # PDF Batch-Verarbeitung
│   │   └── e5_mistral_utils.py        # E5-Mistral Fine-Tuning
│   └── tests/
│       └── test_chunking.py           # Chunking-Tests
│
├── evaluate/                       # Evaluation
│   ├── two_track_evaluation.py     # Two-Track Evaluation
│   ├── evaluate_ontology_compliance.py # Wrapper
│   ├── evaluation_script.py        # Legacy Evaluation
│   └── deduplicate_triples.py      # Tripel-Deduplizierung
│
├── prompt_templates/               # LLM Prompt-Templates
├── few_shot_examples/example/      # Few-Shot-Beispiele
├── schemas/                        # Zielschemas (CSV)
├── datasets/                       # Eingabedaten & Gold-Standard
├── output/                         # Ausgabeverzeichnisse
└── ai/                             # Projektdokumentation & Kontext
    ├── context/                    # Kontextdokumentation (A–D)
    ├── evaluation/                 # Evaluations-JSONs & Logs
    ├── research/                   # Forschungsnotizen
    └── stats/                      # Analyse-Skripte
```
