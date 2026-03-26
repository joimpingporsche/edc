# Änderungen gegenüber dem originalen EDC-Framework

Dieses Dokument beschreibt alle Anpassungen und Erweiterungen, die gegenüber dem originalen [EDC-Framework](https://github.com/clear-nus/EDC) (Commit vor `a91176f`) vorgenommen wurden.

---

## 1. Setup & Umgebung

### `mac_environment.yml` (neu)
- Eigene Conda-Umgebungsdatei für macOS, da `environment.yml` nicht direkt auf dem Mac lauffähig war.

### `a91176f` – Init my fork
- Erste eigene Änderungen an `edc/utils/llm_utils.py` und `edc/edc_framework.py`, um das Projekt lokal auf macOS lauffähig zu machen.

---

## 2. PDF-Preprocessing-Pipeline

### `edc/preprocessing/pdf_to_text_and_tables.py` (neu)
- Neues Skript zum Extrahieren von Text und Tabellen aus Confluence-PDFs.
- Plain-Text-Extraktion und JSON-basierte Tabellen-Extraktion als Ausgabe pro PDF.
- Erzeugt pro Dokument eine `*_combined.txt`-Datei (Text + Tabellen zusammengeführt), eine `*_plain_text.txt` sowie eine `*_tables.jsonl`.

### `datasets/intern/pdfs/` (neu)
- 19 LeanIX-Confluence-PDFs als interner Datensatz hinzugefügt.

### `datasets/intern/text/2_preprocessed/` (neu)
- Vorverarbeitete Textausgaben aller PDFs (plain text, tables, combined) als Ergebnis des PDF-Preprocessings.

---

## 3. Chunking

### `edc/preprocessing/chunking_v1.py` (neu)
- Baseline-Chunking: Sentence-Window- und Character-Window-Modus.
- Unterstützt überlappende Fenster (sliding window).

### `edc/preprocessing/chunking_v2.py` (neu)
- Erweitertes, struktur-bewusstes Chunking:
  - Erkennt Abschnitte (`[SECTION_START]`/`[SECTION_END]`-Marker), Bullet-Listen und Tabellen-JSON-Blöcke.
  - Parameter: `max_chunk_chars`, `min_chunk_chars`, `bullet_group_size`, `prose_window_sentences`, `prose_overlap_sentences`, `table_rows_per_chunk`.
  - Hängt Abschnitts-Titel als Kontext-Präfix an jeden Chunk.
  - Setzt eine Mindest-Chunk-Größe, um zu kleine, informationsarme Blöcke zu verhindern.

### `edc/tests/test_chunking.py` (neu)
- Unit-Tests für beide Chunking-Varianten.

---

## 4. Neuer Einstiegspunkt `run_new.py`

**Ersetzt / erweitert `run.py` für den internen Anwendungsfall:**

- **Dokument-Modi** (`--document_mode`):
  - `test`: Einzelne Textdatei wie im Original.
  - `all_combined`: Lädt alle `*_combined.txt`-Dateien rekursiv aus einem Verzeichnis.
- **Integriertes Chunking** vor dem EDC-Lauf:
  - Wählt Chunking-Variante (`--chunking_variant v1` oder `v2`).
  - Alle Chunking-Parameter über CLI konfigurierbar.
  - Schreibt `chunks_vX.jsonl` und `chunks_text_for_edc_vX.txt` in den Output-Ordner.
- **Neuer `--disable_dc`-Flag**: Überspringt Schema-Definition und Kanonisierung, führt nur OIE durch.
- **Triple Utility Filter**-Parameter direkt im neuen Einstiegspunkt konfigurierbar.
- **Logging der Run-Settings** in `run_settings.log` mit Timestamp.
- **Abstraktion über `load_documents()`** und `build_chunks()`-Hilfsfunktionen.

---

## 5. Azure-Embeddings-Unterstützung

### `edc/utils/llm_utils.py`
- Neue Klasse `AzureEmbeddingModel`: SentenceTransformer-kompatibler Adapter für Azure OpenAI Embeddings.
  - Normalisiert Embeddings auf Einheitslänge.
  - Liest Credentials aus Umgebungsvariablen (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`).
- Unterstützt optionalen `api_version`-Parameter mit Fallback auf `AZURE_OPENAI_API_VERSION`.

### `run.py` / `run_new.py`
- Neuer CLI-Parameter `--embedding_api` (`local` | `azure`).
- Neuer CLI-Parameter `--azure_openai_api_version`.

### `edc/edc_framework.py`
- `load_model()` wählt je nach `embedding_api`-Setting zwischen `SentenceTransformer` und `AzureEmbeddingModel`.
- `free_model()` für SC-Embedder und SR-Embedder wird bei Azure-API übersprungen (kein lokales Modell zu entladen).

---

## 6. Erweiterungen in `edc/edc_framework.py`

### 6.1 `disable_dc`-Modus
- Neuer Parameter `disable_dc` (String oder Bool).
- Falls aktiviert: Schema-Definition und Kanonisierung werden übersprungen; OIE-Tripel werden direkt als Ergebnis weitergegeben.

### 6.2 OIE-Deduplizierung
- Nach dem OIE-Schritt werden Duplikate pro Input-Text entfernt (Reihenfolge bleibt erhalten).
- Anzahl entfernter Duplikate wird geloggt.

### 6.3 Konfigurierbare Kanonisierungs-Parameter
- `sc_top_k`: Anzahl der abgerufenen Kandidaten vor der LLM-Verifikation (vorher hardcoded 5).
- `sc_min_similarity`: Minimale Ähnlichkeit für Kanonisierungsversuch.
- `sc_min_margin`: Mindestabstand zwischen Top-1- und Top-2-Score.

### 6.4 `_build_triplet_change_trace()`
- Neue Hilfsmethode, die vor/nach einem Filterschritt zählt und auflistet:
  - Unveränderte, entfernte und hinzugefügte Tripel.
  - Geschätzte Anzahl umgeschriebener Tripel.
- Ergebnis wird in `result_at_each_stage.json` gespeichert (`utility_filter_trace`).

### 6.5 Output-Verzeichnis-Handling
- Output-Verzeichnisse werden nun immer angelegt (auch wenn das Verzeichnis bereits existiert), statt nur beim ersten Lauf.

---

## 7. Erweiterungen in `edc/schema_canonicalization.py`

### Konfigurierbare Parameter
- `sc_top_k`, `sc_min_similarity`, `sc_min_margin` als Konstruktor-Parameter hinzugefügt.

### Confidence Gate (`_passes_confidence_gate()`)
- Neue Methode: Tripel werden nur kanonisiert, wenn der beste Kandidaten-Score über `sc_min_similarity` liegt und der Margin zwischen Top-1 und Top-2 mindestens `sc_min_margin` beträgt.
- Tripel, die das Gate nicht passieren, werden als `None` (nicht kanonisierbar) behandelt.

### Embedder-Kompatibilität
- `getattr(self.embedder, "prompts", {})` statt direktem Attributzugriff – damit funktioniert `AzureEmbeddingModel` als Drop-in-Ersatz.

### Bugfix: `sc_verify_model` geladen als `"hf"` statt `"sts"`
- Vorher wurde das LLM-Verifikationsmodell fälschlicherweise als Sentence-Transformer geladen.

---

## 8. Neuer EDC-Schritt: Triple Utility Filter

### `edc/triple_utility_filter.py` (neu)
- Neuer LLM-basierter Filterschritt, der nach Kanonisierung oder OIE-only-Lauf ausgeführt werden kann.
- Filtert Tripel, die für ein EA-Schema nicht nützlich sind (z. B. zu konkret, zu spezifisch, keine Ontologie-relevante Aussage).
- Unterstützt HuggingFace- und OpenAI-Modelle.
- Gibt gefiltertes Ergebnis und `parse_ok`-Flag zurück (Fallback auf ungefilterte Tripel bei Parse-Fehler).

### `edc/edc_framework.py` – `triple_utility_filter()`
- Neue Methode, die den oben genannten Filter auf die gesamte Input-Liste anwendet.
- Leere Tripel-Einträge werden übersprungen.
- Ergebnis wird in `useful_kg.txt` geschrieben.
- Anzahl verworfener Tripel wird geloggt.

### `prompt_templates/tu_filter_template.txt` (neu)
- Prompt-Template für den Triple Utility Filter.

### `few_shot_examples/example/tu_few_shot_schema_level.txt` (neu)
- Few-Shot-Beispiele für den Triple Utility Filter auf Schema-Ebene.

---

## 9. Angepasste OIE-Prompts und Few-Shot-Beispiele

### `prompt_templates/oie_schema_level1.txt` / `oie_schema_level2.txt` (neu)
- Neuer Schema-Level-OIE-Prompt: Strikte Regeln, welche Tripel als relevant gelten (kein SAFe, TOGAF, LeanIX-interne Begriffe, keine zu konkreten Implementierungsdetails).
- `oie_schema_level2.txt`: Noch restriktivere Variante mit expliziten Ausschlüssen.

### `few_shot_examples/example/oie_few_shot_schema_level.txt` (neu)
- Angepasste Few-Shot-Beispiele passend zum Schema-Level-OIE-Prompt für den internen Datensatz (LeanIX-Ontologie).

---

## 10. Gold-Datensatz und Hilfsskripte

### `datasets/intern/gold/leanix_ontology.ttl` / `leanix_ontology_cleaned.ttl` (neu)
- LeanIX-Ontologie als TTL-Datei (Referenz-Schema für die Evaluation).

### `edc/utils/ttl_to_gold_txt.py` (neu)
- Konvertiert eine TTL-Ontologie in eine Tripel-Textdatei im EDC-Ausgabeformat (für die Evaluation als Gold-Standard).

### `edc/utils/extract_relation_definitions.py` (neu)
- Extrahiert Relation-Definitionen aus einer TTL-Datei als JSON.

### `edc/utils/extract_gold_relation_comments.py` (neu)
- Extrahiert `rdfs:comment`-Annotationen aus der TTL-Ontologie als strukturierte Relation-Definitionen.

### `edc/utils/align_relation_definitions.py` (neu)
- Aligniert die vom EDC erzeugten Relation-Definitionen mit den Gold-Relation-Definitionen aus der Ontologie via Embedding-Ähnlichkeit.
- Erstellt ein Alignment-JSON für die anschließende Evaluation.

### `edc/utils/run_pdf_batch.py` (neu)
- Hilfsskript zum Stapelverarbeitungs-Preprocessing mehrerer PDFs.

---

## 11. Evaluierungs-Infrastruktur

### `evaluate/evaluate_ontology_compliance.py` (neu, ~307 Zeilen)
- Bewertet, wie gut die extrahierten Tripel mit der LeanIX-Ontologie übereinstimmen.
- Prüft: bekannte Relationen, alignierte Relationen (über `alignment_json`), Domänen-/Bereichs-Compliance, Entitäts-Ähnlichkeit.
- Ausgabe: JSON-Bericht mit Compliance-Rates pro Kategorie.

### `evaluate/two_track_evaluation.py` (neu, ~1165 Zeilen)
- Umfangreiches Zwei-Spur-Evaluierungsskript:
  - **Spur 1**: Vergleicht extrahierte Tripel gegen Gold-Tripel (Precision, Recall, F1 – mit konfigurierbarem Embedding-Ähnlichkeitsschwellenwert für Entitäten und Relationen).
  - **Spur 2**: Bewertet Ontologie-Compliance (bekannte Relationen, alignierte Relationen, Domänen-/Bereichs-Compliance).
  - Integriert optionale KI-Annotationen (CSV mit manuellen Labels).
  - Gibt kombinierten JSON-Bericht aus.

### `evaluate/deduplicate_triples.py` (neu)
- Dedupliziert Tripel in einer EDC-Ausgabedatei global (über alle Chunks hinweg).
- Schreibt deduplizierte Ausgabe in neue Datei.

### `evaluate/README.md`
- Stark erweitert: Beschreibt alle neuen Evaluierungs-Skripte mit CLI-Parametern und Beispielen.

---

## 12. Sonstiges

### `befehle.txt` (neu)
- Interne Befehlsreferenz: Alle wichtigen CLI-Befehle für Preprocessing, EDC-Lauf und Evaluation gesammelt.

### `input_text_example.txt` (neu)
- Beispiel-Eingabedatei mit preprocessed LeanIX-Confluence-Text für schnelle Tests.

### `.gitignore`
- Angepasst (Details nicht explizit dokumentiert).

---

## 13. Output-Ordner – Zuordnung zu Änderungen

Jeder Ordner in `output/` entspricht einem konkreten Experiment-Lauf. Alle Läufe nutzen 22 Dokumente (LeanIX Confluence-PDFs), Chunking v2 und GPT-4.1-mini als OIE-/SC-Modell.

| Output-Ordner | Datum | OIE-Prompt | DC-Phase | Triple Utility Filter | Besonderheiten |
|---|---|---|---|---|---|
| `test_Digital_Solution_with_Chunking` | früh | `oie_template.txt` (original) | ✅ an | ❌ | Erster Chunking-Test, nur Dokument „Digital Solution" |
| `test_Digital_Solution_with_Chunking2` | früh | `oie_template.txt` (original) | ✅ an | ❌ | Zweiter Chunking-Test, nur „Digital Solution" |
| `test_Digital_Solution_with_Chunking3` | früh | `oie_template.txt` (original) | ✅ an | ❌ | Dritter Chunking-Test, nur „Digital Solution" |
| `chunking_debug/` | früh | – | – | – | Reine Chunking-Debug-Ausgaben (v1/v2 Vergleich für „Digital Solution") |
| `all_combined1` | 20.03.2026 | `oie_template.txt` (original) | ✅ an | ❌ | Erster vollständiger Lauf über alle 22 Dokumente; 411 Chunks |
| `all_combined2` | 20.03.2026 | `oie_template.txt` (original) | ✅ an | ❌ | Wie `all_combined1`, aber mit angepasster Mindest-Chunk-Größe → 409 Chunks; **finales Ergebnis von Iteration 1**, Basis für spätere Evaluationen |
| `all_combined3` | 23.03.2026 | `oie_schema_level.txt` + `oie_few_shot_schema_level.txt` (neu: LeanIX-spezifisch) | ✅ an | ❌ | Erster Lauf mit neuem Schema-Level-OIE-Prompt |
| `all_combined4` | 23.03.2026 | `oie_schema_level.txt` + explizite Ausschlüsse (SAFe, TOGAF, LeanIX, BIC) | ✅ an | ❌ | OIE-Prompt mit expliziten Ausschluss-Regeln; hier wurde das Relation-Definition-Alignment (`relation_definition_alignment_2.json`) erzeugt |
| `all_combined5` | 25.03.2026 | `oie_schema_level.txt` | ❌ `disable_dc=True` | ✅ `tu_filter_template.txt` | Erster Lauf mit deaktivierter DC-Phase + aktiviertem Triple Utility Filter; erzeugt `useful_kg.txt` und `useful_kg_dedup.txt` |
| `all_combined_prompt1` | 25.03.2026 | `oie_schema_level1.txt` | ❌ `disable_dc=True` | ❌ | Neuer, überarbeiteter Schema-Level-Prompt (v1); `sc_top_k=3`, `sc_min_similarity=0.45`, `sc_min_margin=0.08` |
| `all_combined_prompt2` | 25.03.2026 | `oie_schema_level2.txt` (striktere Variante) | ❌ `disable_dc=True` | ❌ | Noch restriktiverer OIE-Prompt; gleiche SC-Parameter wie `prompt1` |
| `all_combined_prompt2_with_filter` | 25.03.2026 | `oie_schema_level2.txt` (strikteste Variante) | ❌ `disable_dc=True` | ✅ `tu_filter_template.txt` | Kombination aus striktem Prompt + Triple Utility Filter; erzeugt `useful_kg.txt`/`useful_kg_dedup.txt` |

### Evaluierungsstatus pro Output-Ordner

| Output-Ordner | Ontologie-Compliance-Report | Two-Track-Evaluation | KI-Annotierungen (CSV) |
|---|---|---|---|
| `all_combined1` | ❌ | ❌ | ❌ |
| `all_combined2` | ❌ | ✅ `two_track_eval_report_with_labels.json` | ✅ `ai_eval.csv` |
| `all_combined3` | ❌ | ❌ | ❌ |
| `all_combined4` | ✅ `ontology_eval_report_with_alignment.json` | ✅ `two_track_eval_report_with_labels.json` | ✅ `ai_eval.csv` |
| `all_combined5` | ✅ `ontology_eval_report_with_alignment.json` | ✅ `two_track_eval_report_with_labels.json` | ✅ `ai_eval.csv` |
| `all_combined_prompt1` | ✅ `ontology_eval_report_with_alignment.json` | ❌ | ❌ |
| `all_combined_prompt2` | ✅ `ontology_eval_report_with_alignment.json` | ❌ | ❌ |
| `all_combined_prompt2_with_filter` | ✅ `ontology_eval_report_with_alignment.json` | ✅ `two_track_eval_report_with_labels.json` | ✅ `ai_csv_evaluation.csv` |

---

## Übersicht der Commit-Historie (eigene Commits)

| Commit | Beschreibung |
|---|---|
| `d2740e5` | Projekt läuft komplett durch (erster End-to-End-Test) |
| `6ca471c` | PDF-zu-Text-Preprocessing implementiert (Confluence-PDFs) |
| `c3d509f` | Alle PDFs hinzugefügt und vorverarbeitet |
| `3f617c8` | Chunking-Dateien initial angelegt |
| `9b05d6e` | Chunking v1 & v2 implementiert; `run_chunking.py` (Vorläufer von `run_new.py`) |
| `fdbdbc8` | Azure Embeddings implementiert |
| `c648b70` | Kanonisierungsanpassungen: neuer Prompt, neue Konfigurationsparameter |
| `db5f280` | Chunking mit minimaler Chunk-Größe angepasst; erster vollständiger Lauf |
| `c190b61` | Test-Commit |
| `be66027` | `ttl_to_gold_txt.py` implementiert |
| `7960671` | all_combined2 als finaler Output von Iteration 1 |
| `cb1aacc` | Neuer OIE-Prompt + Few-Shot-Beispiele → all_combined3 |
| `45bc902` | OIE-Prompt angepasst (explizite Ausschlüsse) → all_combined4 |
| `98e9717` | Evaluierungsskript implementiert (`evaluate_ontology_compliance.py`) |
| `5bf2019` | Semantische Evaluation mit Embeddings implementiert |
| `dfce52f` | Projekt-Cleanup |
| `de7518f` | OIE-Deduplizierung + `disable_dc`-Modus implementiert |
| `399327c` | Triple Utility Filter als neuer EDC-Schritt implementiert |
| `3978fd5` | Neuer OIE-Prompt mit strengeren Regeln → all_combined_prompt2_with_filter |
| `7b7ae68` | Zwei-Spur-Evaluation implementiert und für alle neusten Läufe ausgeführt |
| `e682829` | all_combined2 evaluiert; finaler Vergleichsbericht |
