# EDC Evaluation Run Comparison

Dieses Dokument vergleicht alle Evaluationsläufe chronologisch. Für jeden Run werden
die Settings, Änderungen gegenüber dem Vorgänger sowie die wichtigsten Evaluationsmetriken
dokumentiert.

---

## Gesamtübersicht

| Run | Datum | Chunks | Ø Chunk-Länge | Triples total | Triples (unique) | Matched | novel | Eval-Pipeline | Sample |
|-----|-------|--------|---------------|--------------|-------------------|---------|-------|---------------|--------|
| [all_combined1](#run-1--all_combined1) | 2026-03-20 | 411 | 463 ch | 2 523 | 2 523 | 16 | 2 507 | neu (run_evaluation.py) | 100 |
| [all_combined2](#run-2--all_combined2) | 2026-03-20 | 409 | 464 ch | 2 472 | 2 472 | 15 | 2 457 | alt (two_track) | 50 |
| [all_combined3](#run-3--all_combined3-kein-eval) | 2026-03-23 | 409 | 464 ch | – | – | – | – | – | – |
| [all_combined4](#run-4--all_combined4) | 2026-03-23 | 409 | 464 ch | 1 509 | 1 509 | 12 | 1 497 | alt (two_track) | 50 |
| [all_combined5](#run-5--all_combined5) | 2026-03-25 | 409 | 464 ch | 1 160 | 1 160 | 34 | 1 126 | alt (two_track) | 50 |
| [all_combined_prompt2_with_filter](#run-6--all_combined_prompt2_with_filter) | 2026-03-25 | 409 | 464 ch | 516 | 516 | 31 | 485 | alt (two_track) | 50 |
| […dc_chunks_normal](#run-7--all_combined_prompt2_with_filter_with_dc_chunks_normal) | 2026-03-27 | 409 | 464 ch | 518 | 518 | 31 | 487 | neu (run_evaluation.py) | 100 |
| […dc_chunks_500](#run-8--all_combined_prompt2_with_filter_with_dc_chunks_500) | 2026-03-27 | 303 | 600 ch | 547 | 547 | 37 | 510 | neu (run_evaluation.py) | 100 |

### Hinweise zur Vergleichbarkeit

- **Alte Eval-Pipeline** (`two_track_evaluation.py` → `two_track_eval_report_with_labels.json`): 50 Stichproben, direkter LLM-/Mensch-Label-Import.
- **Neue Eval-Pipeline** (`run_evaluation.py` → `eval_report_final.json`): 100 Stichproben (stratifiziert), automatisches LLM-Labeling per `run_evaluation.py`. Metriken werden nach zwei Passes (Pass 1 ohne Labels → LLM-Labeling → Pass 2 mit Labels) berechnet.
- `enrichment_precision` ist zwischen alter (50 Samples) und neuer (100 Samples) Pipeline nur bedingt direkt vergleichbar.
- Runs 1–4 extrahieren aus `canon_kg_dedup.txt` (nach Schema-Canonicalization); Runs 5–8 aus `useful_kg_dedup.txt` (nach zusätzlichem Triple-Utility-Filter).

---

## Kennzahlen-Vergleich (Metriken)

| Run | Align. Precision | Align. Recall | Align. F1 | Relation Valid Rate | Domain Valid Rate | Range Valid Rate | Ontology Coverage | Enrich. Prec. | Enrich. Prec. strict | SUPPORTED | PARTIAL | UNSUPP. |
|-----|-----------------|---------------|-----------|---------------------|-------------------|------------------|-------------------|---------------|----------------------|-----------|---------|---------|
| all_combined1 | 53.3 % | 1.7 % | 3.3 % | 8.8 % | 1.4 % | 0.9 % | 1.4 % | 63.0 % | 74.1 % | 63 | 15 | 22 |
| all_combined2 | 57.7 % | 1.6 % | 3.1 % | 8.5 % | 0.9 % | 0.9 % | 1.4 % | 66.0 % | 73.3 % | 33 | 5 | 12 |
| all_combined3 | – | – | – | – | – | – | – | – | – | – | – | – |
| all_combined4 | 50.0 % | 1.3 % | 2.5 % | 13.9 % | 2.3 % | 1.3 % | 1.3 % | 52.0 % | 65.0 % | 26 | 10 | 14 |
| all_combined5 | 29.3 % | 3.6 % | 6.5 % | **81.7 %** | 16.3 % | 7.8 % | 3.5 % | 28.0 % | 35.0 % | 14 | 10 | 26 |
| prompt2_with_filter | 29.2 % | 3.3 % | 6.0 % | 80.4 % | 23.8 % | 13.4 % | 3.2 % | 40.0 % | 48.8 % | 20 | 9 | 21 |
| dc_chunks_normal | 29.2 % | 3.3 % | 6.0 % | 80.5 % | 24.7 % | 13.9 % | 3.2 % | 58.0 % | **80.6 %** | 58 | 28 | 14 |
| dc_chunks_500 | **30.8 %** | **4.0 %** | **7.0 %** | 85.0 % | **25.2 %** | **15.5 %** | **3.6 %** | 53.0 % | 67.1 % | 53 | 21 | 26 |

> **Fettgedruckte Werte** markieren das jeweilige Optimum über alle Runs (pro Spalte).

---

## Run 1 – all_combined1

**Datum:** 2026-03-20T10:41:00 UTC  
**Eval-Report:** `output/all_combined1/iter0/eval_report_final.json`  
**Prediction-Datei:** `iter0/canon_kg_dedup.txt`

### Settings

```
chunk_count           = 411
avg_chunk_length_chars= 463.27
chunking_variant      = v2
v2_max_chunk_chars    = 1000
v2_min_chunk_chars    = 120
oie_template          = oie_template.txt
oie_few_shot          = oie_few_shot_examples.txt
disable_dc            = (nicht gesetzt – Standard: DC aktiv)
enable_triple_utility_filter = (nicht gesetzt – kein Filter)
```

### Änderungen gegenüber Vorgänger

> Erster Run – kein Vorgänger.

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 2 523 / 2 523 |
| Matched (Alignment) | 16 |
| Novel triples | 2 507 |
| Alignable predictions | 30 |
| Alignment Precision | 53.3 % |
| Alignment Recall | 1.7 % |
| Alignment F1 | 3.3 % |
| Relation Valid Rate | 8.8 % |
| Domain Valid Rate | 1.4 % |
| Range Valid Rate | 0.9 % |
| Ontology Coverage | 1.4 % |
| **Enrichment Precision** | **63.0 %** |
| Enrichment Precision (strict) | 74.1 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 63 / 15 / 22 |
| Novel unique predicates | 673 |
| Top-Prädikate | includes (132), type (78), supports (66), description (58), example (58) |

### Beobachtungen

- OIE nutzt den generischen Prompt (`oie_template.txt`) ohne Schema-Bezug.
- Sehr hohe Zahl von Novel-Prädikaten (673), darunter viele unsemantische wie `type`, `color`, `description`, `example` – Hinweis auf schlechte Prompt-Steuerung.
- Trotzdem hohe `enrichment_precision` (63 %) bei 100 Samples (neue Eval-Pipeline).
- Niedrige `relation_valid_rate` (8.8 %) zeigt: Der Großteil der Prädikate ist im Gold-Ontologie-Vokabular unbekannt.

---

## Run 2 – all_combined2

**Datum:** 2026-03-20T11:43:27 UTC  
**Eval-Report:** `output/all_combined2/two_track_eval_report_with_labels.json`  
**Prediction-Datei:** `iter0/canon_kg_dedup.txt`

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 1500   ← GEÄNDERT (war 1000)
v2_min_chunk_chars    = 120
oie_template          = oie_template.txt       (unverändert)
oie_few_shot          = oie_few_shot_examples.txt (unverändert)
disable_dc            = (nicht gesetzt)
enable_triple_utility_filter = (nicht gesetzt)
```

### Änderungen gegenüber Run 1

| Parameter | Run 1 | Run 2 |
|-----------|-------|-------|
| `v2_max_chunk_chars` | 1 000 | **1 500** |
| Eval-Pipeline | neu (100 samples) | alt (50 samples) |

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 2 472 / 2 472 |
| Matched (Alignment) | 15 |
| Novel triples | 2 457 |
| Alignment Precision | 57.7 % |
| Alignment Recall | 1.6 % |
| Alignment F1 | 3.1 % |
| Relation Valid Rate | 8.5 % |
| Domain Valid Rate | 0.9 % |
| Range Valid Rate | 0.9 % |
| Ontology Coverage | 1.4 % |
| **Enrichment Precision** | **66.0 %** |
| Enrichment Precision (strict) | 73.3 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 33 / 5 / 12 |
| Novel unique predicates | 673 |
| Top-Prädikate | includes (132), type (87), supports (62), description (59), purpose (44) |

### Beobachtungen

- Minimal weniger Triples als Run 1 (2 523 → 2 472) – vermutlich durch längere Chunks und damit geringfügig andere Segmentierung.
- Metriken nahezu identisch; Verbesserung bei `alignment_precision` (53 % → 58 %) könnte auch auf kleinerem Sample (50 vs 100) beruhen.
- Problematik des generischen Prompts bleibt: 673 novel predicates, viele semantisch wertlos.

---

## Run 3 – all_combined3 *(kein Eval)*

**Datum:** 2026-03-23T08:13:06 UTC  
**Eval-Report:** *nicht vorhanden*

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 2000   ← GEÄNDERT (war 1500)
v2_min_chunk_chars    = 120
oie_template          = oie_schema_level.txt   ← NEU (war oie_template.txt)
oie_few_shot          = oie_few_shot_schema_level.txt ← NEU
disable_dc            = (nicht gesetzt)
enable_triple_utility_filter = (nicht gesetzt)
```

### Änderungen gegenüber Run 2

| Parameter | Run 2 | Run 3 |
|-----------|-------|-------|
| `v2_max_chunk_chars` | 1 500 | **2 000** |
| `oie_prompt_template_file_path` | `oie_template.txt` | **`oie_schema_level.txt`** |
| `oie_few_shot_example_file_path` | `oie_few_shot_examples.txt` | **`oie_few_shot_schema_level.txt`** |

### Beobachtungen

- Großer konzeptioneller Wechsel: OIE wird jetzt schema-level gesteuert – der Prompt kennt das Zielschema und soll Prädikate aus dem Schema verwenden.
- Kein Evaluationsbericht. Run 3 war vermutlich ein erster Testlauf mit dem neuen Prompt; Run 4 (gleiche Settings) folgte unmittelbar danach mit Evaluation.

---

## Run 4 – all_combined4

**Datum:** 2026-03-23T09:15:34 UTC  
**Eval-Report:** `output/all_combined4/two_track_eval_report_with_labels.json`  
**Prediction-Datei:** `iter0/canon_kg_dedup_global.txt`

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 2000
v2_min_chunk_chars    = 120
oie_template          = oie_schema_level.txt
oie_few_shot          = oie_few_shot_schema_level.txt
disable_dc            = (nicht gesetzt)
enable_triple_utility_filter = (nicht gesetzt)
```

### Änderungen gegenüber Run 3

*Keine Parameteränderungen* – identische Settings. Run 4 ist eine Wiederholung von Run 3 mit anschließender Evaluation (Run 3 hatte kein Eval-Ergebnis).

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 1 509 / 1 509 |
| Matched (Alignment) | 12 |
| Novel triples | 1 497 |
| Alignable predictions | 24 |
| Alignment Precision | 50.0 % |
| Alignment Recall | 1.3 % |
| Alignment F1 | 2.5 % |
| Relation Valid Rate | 13.9 % |
| Domain Valid Rate | 2.3 % |
| Range Valid Rate | 1.3 % |
| Ontology Coverage | 1.3 % |
| **Enrichment Precision** | **52.0 %** |
| Enrichment Precision (strict) | 65.0 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 26 / 10 / 14 |
| Novel unique predicates | 378 |
| Top-Prädikate | includes (109), supports (83), has type (43), enables (38), linked to (36) |

### Beobachtungen

- Schema-level OIE reduziert die Tripel-Zahl deutlich (2 472 → 1 509) und die Anzahl novel predicates stark (673 → 378).
- `relation_valid_rate` steigt von 8.5 % auf 13.9 % – Prädikate sind näher am Schema.
- Allerdings sinkt `enrichment_precision` (66 % → 52 %) – der neue Prompt erzeugt strukturell sauberere aber inhaltlich weniger präzise Triples.
- Prädikate sind immer noch sehr divers; viele wie `has type`, `has attribute`, `has field` sind ontologie-fremd.

---

## Run 5 – all_combined5

**Datum:** 2026-03-25T10:11:37 UTC  
**Eval-Report:** `output/all_combined5/two_track_eval_report_with_labels.json`  
**Prediction-Datei:** `iter0/useful_kg_dedup.txt` *(nach Triple-Utility-Filter)*

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 2000
v2_min_chunk_chars    = 120
oie_template          = oie_schema_level.txt
oie_few_shot          = oie_few_shot_schema_level.txt
disable_dc            = True    ← NEU (DC deaktiviert)
enable_triple_utility_filter = True ← NEU (TU-Filter aktiviert)
tu_llm                = gpt-4.1-mini
tu_few_shot           = tu_few_shot_schema_level.txt
tu_template           = tu_filter_template.txt
```

### Änderungen gegenüber Run 4

| Parameter | Run 4 | Run 5 |
|-----------|-------|-------|
| `disable_dc` | (nicht gesetzt) | **`True`** |
| `enable_triple_utility_filter` | (nicht gesetzt) | **`True`** |

> **`disable_dc=True`**: Document-Context-Schritt wird übersprungen.  
> **`enable_triple_utility_filter=True`**: Nach OIE werden Triples durch einen LLM-basierten Utility-Filter (`tu_filter_template.txt`) gefiltert; das Ergebnis landet in `useful_kg.txt` statt `canon_kg.txt`.

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 1 160 / 1 160 |
| Matched (Alignment) | 34 |
| Novel triples | 1 126 |
| Alignable predictions | 116 |
| Alignment Precision | 29.3 % |
| Alignment Recall | 3.6 % |
| Alignment F1 | 6.5 % |
| **Relation Valid Rate** | **81.7 %** |
| Domain Valid Rate | 16.3 % |
| Range Valid Rate | 7.8 % |
| Ontology Coverage | 3.5 % |
| Enrichment Precision | 28.0 % |
| Enrichment Precision (strict) | 35.0 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 14 / 10 / 26 |
| Novel unique predicates | 110 |
| Top-Prädikate | consists of (136), classifies (125), supports (117), responsible for (77), provides (63) |

### Beobachtungen

- **Größter Sprung in `relation_valid_rate`**: von 13.9 % auf **81.7 %**. Der Triple-Utility-Filter entfernt offensichtlich die semantisch wertlosen Triples sehr effektiv.
- Novel predicates: drastische Reduktion von 378 auf **110** – Prädikate sind jetzt viel fokussierter und schema-näher.
- `alignment_precision` sinkt (50 % → 29 %): trotz besserer Relation-Gültigkeit treffen die verbleibenden 116 alignierbaren Triples weniger oft genau ins Gold.
- `enrichment_precision` sinkt von 52 % auf 28 %. Ursache: Der Filter behält zwar ontologisch sinnvolle Prädikate, aber die entities (Domain/Range) passen oft nicht zum Gold-Ontologie-Schema.
- `domain_valid_rate` und `range_valid_rate` steigen (2.3 % → 16.3 % / 1.3 % → 7.8 %), der Großteil der Verletzungen kommt von bekannten Relationen mit falschen Entitätskombinationen (`known_relation_but_subject_and_object_not_allowed`: 701 Fälle).

---

## Run 6 – all_combined_prompt2_with_filter

**Datum:** 2026-03-25T11:56:21 UTC  
**Eval-Report:** `output/all_combined_prompt2_with_filter/two_track_eval_report_with_labels.json`  
**Prediction-Datei:** `iter0/useful_kg_dedup.txt`

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 2000
v2_min_chunk_chars    = 120
oie_template          = oie_schema_level2.txt  ← NEU (war oie_schema_level.txt)
oie_few_shot          = oie_few_shot_schema_level.txt (unverändert)
disable_dc            = True
enable_triple_utility_filter = True
```

### Änderungen gegenüber Run 5

| Parameter | Run 5 | Run 6 |
|-----------|-------|-------|
| `oie_prompt_template_file_path` | `oie_schema_level.txt` | **`oie_schema_level2.txt`** |

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 516 / 516 |
| Matched (Alignment) | 31 |
| Novel triples | 485 |
| Alignable predictions | 106 |
| Alignment Precision | 29.2 % |
| Alignment Recall | 3.3 % |
| Alignment F1 | 6.0 % |
| Relation Valid Rate | 80.4 % |
| Domain Valid Rate | 23.8 % |
| Range Valid Rate | 13.4 % |
| Ontology Coverage | 3.2 % |
| **Enrichment Precision** | **40.0 %** |
| Enrichment Precision (strict) | 48.8 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 20 / 9 / 21 |
| Novel unique predicates | 62 |
| Top-Prädikate | consists of (72), supports (67), affects (37), realizes (29), provides (27) |

### Beobachtungen

- OIE Prompt v2 (`oie_schema_level2.txt`) reduziert die Tripelmenge nochmals stark: 1 160 → **516 Triples** (−55 %).
- Novel predicates sinken auf 62 – die generierten Prädikate sind deutlich schema-konformer.
- `domain_valid_rate` und `range_valid_rate` steigen spürbar (16.3 % → 23.8 % / 7.8 % → 13.4 %).
- `enrichment_precision` steigt von 28 % auf 40 % (bei gleicher alter Pipeline, 50 Samples) – trotz weniger Triples mehr inhaltlich valide Novel-Triples.
- `alignment_precision` bleibt auf gleichem Niveau (~29 %).

---

## Run 7 – all_combined_prompt2_with_filter_with_dc_chunks_normal

**Datum:** 2026-03-27T10:05:22 UTC  
**Eval-Report:** `output/all_combined_prompt2_with_filter_with_dc_chunks_normal/iter0/eval_report_final.json`  
**Prediction-Datei:** `iter0/useful_kg_dedup.txt`

### Settings

```
chunk_count           = 409
avg_chunk_length_chars= 463.83
v2_max_chunk_chars    = 2000
v2_min_chunk_chars    = 120
oie_template          = oie_schema_level2.txt
oie_few_shot          = oie_few_shot_schema_level.txt
disable_dc            = False   ← GEÄNDERT (war True → DC reaktiviert)
enable_triple_utility_filter = True
```

### Änderungen gegenüber Run 6

| Parameter | Run 6 | Run 7 |
|-----------|-------|-------|
| `disable_dc` | `True` | **`False`** (DC wieder aktiv) |
| Eval-Pipeline | alt (50 samples) | **neu (100 samples, run_evaluation.py)** |

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 518 / 518 |
| Matched (Alignment) | 31 |
| Novel triples | 487 |
| Alignable predictions | 106 |
| Alignment Precision | 29.2 % |
| Alignment Recall | 3.3 % |
| Alignment F1 | 6.0 % |
| Relation Valid Rate | 80.5 % |
| Domain Valid Rate | 24.7 % |
| Range Valid Rate | 13.9 % |
| Ontology Coverage | 3.2 % |
| **Enrichment Precision** | **58.0 %** |
| Enrichment Precision (strict) | **80.6 %** |
| SUPPORTED / PARTIAL / UNSUPPORTED | 58 / 28 / 14 |
| Novel unique predicates | 66 |
| Top-Prädikate | consists of (73), supports (66), affects (35), classifies (32), realizes (30) |

### Beobachtungen

- DC-Reaktivierung hat **kaum Einfluss auf die Tripel-Zahl** (516 → 518) und objektive Metriken. Prädikate, Domain/Range-Quoten bleiben nahezu identisch zu Run 6.
- **Enrichment Precision steigt deutlich**: 40 % → 58 % (alt→neu, aber auch 50→100 Samples). Der Großteil des Anstiegs ist zumindest teilweise auf den Wechsel zur neuen Eval-Pipeline (100 Samples, genauere Stratifizierung) zurückzuführen.
- `enrichment_precision_strict` (80.6 %) ist der höchste Wert aller Runs.
- UNSUPPORTED-Triples sinken auf 14 – niedrigstes Niveau aller Runs.

---

## Run 8 – all_combined_prompt2_with_filter_with_dc_chunks_500

**Datum:** 2026-03-27T10:21:42 UTC  
**Eval-Report:** `output/all_combined_prompt2_with_filter_with_dc_chunks_500/iter0/eval_report_final.json`  
**Prediction-Datei:** `iter0/useful_kg_dedup.txt`

### Settings

```
chunk_count           = 303      ← GEÄNDERT (war 409; −26 % Chunks)
avg_chunk_length_chars= 599.59   ← GEÄNDERT (war 463.83; +29 %)
v2_max_chunk_chars    = 2000
v2_min_chunk_chars    = 700      ← GEÄNDERT (war 120)
oie_template          = oie_schema_level2.txt
oie_few_shot          = oie_few_shot_schema_level.txt
disable_dc            = False
enable_triple_utility_filter = True
```

### Änderungen gegenüber Run 7

| Parameter | Run 7 | Run 8 |
|-----------|-------|-------|
| `v2_min_chunk_chars` | 120 | **700** |
| `chunk_count` | 409 | **303** (−26 %) |
| `avg_chunk_length_chars` | 463.83 | **599.59** (+29 %) |

> **Effekt**: Kleine Chunks (< 700 Zeichen) werden nicht mehr als eigenständige Chunks ausgegeben/verarbeitet, was z. B. kurze Tabellenzeilen oder Marginalien zusammenfasst. Das reduziert die Chunk-Anzahl und erhöht die durchschnittliche Chunk-Länge.

### Evaluationsergebnisse

| Metrik | Wert |
|--------|------|
| Triples total / unique | 547 / 547 |
| Matched (Alignment) | 37 |
| Novel triples | 510 |
| Alignable predictions | 120 |
| Alignment Precision | 30.8 % |
| Alignment Recall | **4.0 %** |
| Alignment F1 | **7.0 %** |
| **Relation Valid Rate** | **85.0 %** |
| **Domain Valid Rate** | **25.2 %** |
| **Range Valid Rate** | **15.5 %** |
| **Ontology Coverage** | **3.6 %** |
| Enrichment Precision | 53.0 % |
| Enrichment Precision (strict) | 67.1 % |
| SUPPORTED / PARTIAL / UNSUPPORTED | 53 / 21 / 26 |
| Novel unique predicates | 54 |
| Top-Prädikate | consists of (81), supports (62), affects (42), classifies (37), provides (34) |

### Beobachtungen

- Größere Mindest-Chunks steigern die Tripelzahl leicht (518 → 547) und die Anzahl alignierbarer Predictions (106 → 120) → mehr Matches (31 → 37).
- **Beste alignment-bezogene Metriken** aller Runs: Recall (4.0 %), F1 (7.0 %), `relation_valid_rate` (85.0 %), `domain_valid_rate` (25.2 %), `range_valid_rate` (15.5 %), `ontology_coverage` (3.6 %).
- `enrichment_precision` sinkt leicht gegenüber Run 7 (58 % → 53 %). Mögliche Ursache: Größere Chunks enthalten mehr Kontext, was zu mehr aber auch ungenaueren Novel-Triples führt.
- Novel predicates auf 54 gesunken – kleinstes Vokabular aller Runs.

---

## Zusammenfassung der Experimentrierhistorie

```
Run 1 →(+max_chunk)→ Run 2 →(schema-OIE, +max_chunk)→ Run 3/4 →(+TU-Filter, -DC)→ Run 5
      →(OIE-Prompt v2)→ Run 6 →(+DC)→ Run 7 →(+min_chunk_700)→ Run 8
```

### Wichtigste Erkenntnisse

1. **Schema-Level OIE (Run 3/4)** reduziert die Anzahl der Triples und novel predicates erheblich, bringt aber deutliche Verbesserungen in `relation_valid_rate` und Prädikat-Kohärenz.

2. **Triple-Utility-Filter (Run 5)** ist die mit Abstand wirksamste Einzelmaßnahme: `relation_valid_rate` steigt von ~14 % auf ~82 %, novel predicates sinken von 378 auf 110.

3. **OIE-Prompt v2 (Run 6)** verfeinert die generierten Prädikate weiter (110 → 62 novel, Triples 1160 → 516) und verbessert Domain/Range-Validität.

4. **DC-Reaktivierung (Run 7)** hat keinen messbaren Einfluss auf die Extraktionsqualität (Tripel-Zahl nahezu gleich), verbessert aber die gemessene Enrichment Precision in der neuen Pipeline deutlich (vermutlich durch bessere Quelltextzu­ordnung im LLM-Labeling).

5. **Größere Min-Chunks (Run 8)** verbessern die alignment-bezogenen Metriken (mehr Treffer, besserer Recall) auf Kosten einer leicht niedrigeren Enrichment Precision.

6. **Eval-Pipeline-Wechsel** (alt: 50 Samples → neu: 100 Samples + zweistufig): Die neue Pipeline liefert robustere Enrichment-Precision-Schätzungen. Werte zwischen alter und neuer Pipeline sind nicht direkt vergleichbar.
