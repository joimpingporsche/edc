# EDC-Framework – Projektanalyse

---

## 1. Few-Shot-Beispiel-Dateien (vollständig)

### 1.1 `oie_few_shot_examples.txt` (Iter 0)

**Pfad:** `few_shot_examples/example/oie_few_shot_examples.txt`

> **Achtung:** Dies sind generische WebNLG-Beispiele, keine LeanIX-domänenspezifischen Beispiele.

```
Example 1:
Text: The location of Trane is Swords, Dublin.
Triplets: [['Trane', 'location', 'Swords,_Dublin']]

Example 2:
Text: The Ciudad Ayala city, a part of Morelos with population density and population of 1604.0 and 1,777,539 respectively, has a UTC offset of -6. The government type of Ciudad Ayala is council-manager government and City Manager is one of the leaders.
Triplets: [['Ciudad_Ayala', 'populationMetro', '1777539'], ['Ciudad_Ayala', 'leaderTitle', '"City Manager"'], ['Ciudad_Ayala', 'type', 'City'], ['Ciudad_Ayala', 'populationDensity', '1604.0'], ['Ciudad_Ayala', 'governmentType', 'Council-manager_government'], ['Ciudad_Ayala', 'utcOffset', '−6'], ['Ciudad_Ayala', 'isPartOf', 'Morelos']]

Example 3:
Text: The 17068.8 millimeter long ALCO RS-3 has a diesel-electric transmission.
Triplets: [['ALCO_RS-3', 'powerType', 'Diesel-electric_transmission'], ['ALCO_RS-3', 'length', '17068.8 (millimetres)']]

Example 4:
Text: Alan B. Miller Hall, in Virginia, USA, was designed by Robert A.M. Stern. The address of the hall is "101 Ukrop Way" and the current tenants are the Mason School of Business.
Triplets: [['Alan_B._Miller_Hall', 'architect', 'Robert_A._M._Stern'], ['Alan_B._Miller_Hall', 'address', '"101 Ukrop Way"'], ['Alan_B._Miller_Hall', 'currentTenants', 'Mason_School_of_Business'], ['Alan_B._Miller_Hall', 'location', 'Virginia'], ['Mason_School_of_Business', 'country', 'United_States']]

Example 5:
Text: Liselotte Grschebina was born in Karlsruhe and died in Israel. Ethnic groups in Israel include Arabs.
Triplets: [['Liselotte_Grschebina', 'bornIn', 'Karlsruhe'], ['Liselotte_Grschebina', 'diedIn', 'Israel'], ['Israel', 'ethnicGroup', 'Arab_citizens_of_Israel']]

Example 6:
Text: Agremiação Sportiva Arapiraquense managed by Vica has 17000 members and play in the Campeonato Brasileiro Série C league which is from Brazil.
Triplets: [['Agremiação_Sportiva_Arapiraquense', 'league', 'Campeonato_Brasileiro_Série_C'], ['Campeonato_Brasileiro_Série_C', 'country', 'Brazil'], ['Agremiação_Sportiva_Arapiraquense', 'numberOfMembers', '17000'], ['Agremiação_Sportiva_Arapiraquense', 'manager', 'Vica']]
```

---

### 1.2 `oie_few_shot_schema_level.txt` (Iter 1–3)

**Pfad:** `few_shot_examples/example/oie_few_shot_schema_level.txt`

> **LeanIX-domänenspezifische Beispiele.** Entitäten wie Digital_Solution, IT_Product, Business_Capability etc.

```
Example 1:
Text: A Digital Solution is a cohesive construct that delivers business value by integrating multiple IT Products.
Triplets: [['Digital_Solution', 'delivers', 'Business_Value'], ['Digital_Solution', 'integrates', 'IT_Product']]

Example 2:
Text: In addition to IT Products, a Digital Solution may also include business processes, methods and practices, and organizational structures.
Triplets: [['Digital_Solution', 'mayInclude', 'Business_Process'], ['Digital_Solution', 'mayInclude', 'Method_and_Practice'], ['Digital_Solution', 'mayInclude', 'Organizational_Structure']]

Example 3:
Text: Each IT Product is an application, business service, or business platform, including its associated technologies.
Triplets: [['IT_Product', 'hasType', 'Application'], ['IT_Product', 'hasType', 'Business_Service'], ['IT_Product', 'hasType', 'Business_Platform'], ['IT_Product', 'includes', 'Associated_Technology']]

Example 4:
Text: Each Digital Solution is developed within a single Agile Release Train, managed within one portfolio, and developed by one or more agile teams within a development value stream.
Triplets: [['Digital_Solution', 'developedWithin', 'Agile_Release_Train'], ['Digital_Solution', 'managedWithin', 'Portfolio'], ['Digital_Solution', 'developedBy', 'Agile_Team'], ['Agile_Team', 'partOf', 'Development_Value_Stream']]

Example 5:
Text: Active business processes from a Process Modeling Tool are imported into an Enterprise Architecture Repository. Active IT products from the Enterprise Architecture Repository are exported to the Process Modeling Tool as applications.
Triplets: [['Business_Process', 'importedFrom', 'Process_Modeling_Tool'], ['Business_Process', 'importedTo', 'Enterprise_Architecture_Repository'], ['IT_Product', 'exportedFrom', 'Enterprise_Architecture_Repository'], ['IT_Product', 'exportedTo', 'Process_Modeling_Tool'], ['IT_Product', 'exportedAs', 'Application']]

Example 6:
Text: IT Products support Processes. Processes are linked to Business Capabilities. Initiatives are linked to Processes.
Triplets: [['IT_Product', 'supports', 'Process'], ['Process', 'linkedTo', 'Business_Capability'], ['Initiative', 'linkedTo', 'Process']]
```

---

### 1.3 `tu_few_shot_schema_level.txt` (TU-Filter Few-Shot, Iter 2–3)

**Pfad:** `few_shot_examples/example/tu_few_shot_schema_level.txt`

> **Zeigt dem LLM, welche Tripel zu behalten und welche zu verwerfen sind.** Demonstriert Filterlogik: `hasType` rausfliegen, `supports`/`linkedTo`/`consistsOf` bleiben, Umformulierung zu kanonischen Prädikaten.

```
Example 1:
Input Tripel: [['Digital_Solution', 'consistsOf', 'IT_Product'], ['IT_Product', 'hasType', 'Application'], ['IT_Product', 'supports', 'Business_Capability']]
Output Tripel: [['Digital_Solution', 'consistsOf', 'IT_Product'], ['IT_Product', 'supports', 'Business_Capability']]

Example 2:
Input Tripel: [['Process', 'createdIn', 'Process_Modeling_Tool'], ['Process', 'maintainedIn', 'Process_Modeling_Tool'], ['Process', 'synchronizedTo', 'Architecture_Repository']]
Output Tripel: [['Process', 'synchronizedWith', 'Architecture_Repository']]

Example 3:
Input Tripel: [['Business_Process', 'importedFrom', 'Process_Modeling_Tool'], ['Business_Process', 'receives', 'Enterprise_Architecture_Repository'], ['Business_Process', 'linkedTo', 'Application']]
Output Tripel: [['Business_Process', 'importedTo', 'Enterprise_Architecture_Repository'], ['Business_Process', 'linkedTo', 'Application']]

Example 4:
Input Tripel: [['IT_Product', 'developedBy', 'Agile_Release_Train'], ['IT_Product', 'managedWithin', 'Portfolio'], ['Agile_Release_Train', 'maintainedIn', 'Database']]
Output Tripel: [['IT_Product', 'developedBy', 'Agile_Release_Train'], ['IT_Product', 'managedWithin', 'Portfolio']]

Example 5:
Input Tripel: [['Application', 'supports', 'Business_Process'], ['Application', 'supports', 'Business_Capability'], ['Application', 'mayExpose', 'API']]
Output Tripel: [['Application', 'supports', 'Process'], ['Application', 'supports', 'Business_Capability']]

Example 6:
Input Tripel: [['Digital_Solution', 'developedWithin', 'Agile_Release_Train'], ['Digital_Solution', 'managedWithin', 'Portfolio'], ['Digital_Solution', 'linkedTo', 'Business_Capability']]
Output Tripel: [['Digital_Solution', 'developedWithin', 'Agile_Release_Train'], ['Digital_Solution', 'managedWithin', 'Portfolio']]
```

---

## 2. `enrich_schema=True` – Was bewirkt dieses Flag?

**Quellen:** `edc/edc_framework.py` (Zeile 76, 402), `edc/schema_canonicalization.py` (Zeile 141–202)

Wenn `enrich_schema=True` gesetzt ist, wird die Schema-Datenbank **zur Laufzeit dynamisch erweitert**: Falls ein extrahiertes Tripel eine Relation enthält, die nicht im Ziel-Schema (`example_schema.csv`) kanonisiert werden kann (weder exakter Match noch LLM-verifizierter Kandidat), wird diese neue Relation **mitsamt ihrer vom Schema-Definition-Modul generierten Beschreibung** in `self.schema_dict` und `self.schema_embedding_dict` eingefügt. Dadurch kann das Schema im Laufe einer Iteration wachsen, sodass spätere Chunks diese Relation als kanonisch erkennen.

**In unserem Setup (`refinement_iterations=0`, `disable_dc=True`):**  
Da `disable_dc=True` die gesamte Schema-Definition- und Schema-Canonicalization-Phase überspringt, ist `enrich_schema` ein **No-op** – der betreffende Code-Pfad wird gar nicht erreicht. Die OIE-Tripel werden direkt ohne Kanonisierung ausgegeben. Auch bei `refinement_iterations=0` gibt es keine weiteren Iterationsschleifen, in denen ein erweitertes Schema genutzt werden könnte.

---

## 3. `schemas/example_schema.csv`

**Pfad:** `schemas/example_schema.csv`
**Info:** `Ist EDC original Datei und wurde für mein Projekt und die ausführung nicht verwendet weil enrich_schema=True.`

### Spalten

Zwei Spalten (kein Header): `relation_name, relation_definition`

### Anzahl

**9 Relationen** (9 Zeilen, keine Header-Zeile).

### Vollständiger Inhalt

| Relation | Definition |
|----------|-----------|
| student | The subject receives education at the institute specified by the object entity. |
| country | The subject entity is located in the country specified by the object entity. |
| contains administrative territorial entity | The subject entity contains the administrative territorial entity specified by the object entity. |
| contains settlement | The subject entity contains the settlement specified by the object entity. |
| located in the administrative territorial entity | The subject entity is located in the administrative territorial entity specified by the object entity. |
| date of birth | The subject entity was born on the date specified by the object entity. |
| place of birth | The subject entity was born in the location specified by the object entity. |
| date of death | The subject entity died on the date specified by the object entity. |
| place of death | The subject entity died in the location specified by the object entity. |
| start time | The subject entity began at the time specified by the object entity. |

### LeanIX-Ontologie?

**Nein.** Dies ist die **originale EDC-Beispiel-Schema-Datei** (generisch, Wikidata-artig). Die 31 Prädikate aus dem TU-Filter-Whitelist (z. B. `supports`, `consists_of`, `owned_by`, `requires`, `affects` etc.) sind **nicht** enthalten. Die Datei wird bei `disable_dc=True` ohnehin nicht verwendet.

---

## 4. Datenbasis-Details

### 4.1 PDFs in `datasets/intern/pdfs/` (22 Dateien)

**Infos:** `Diese Dateien stammen aus der ITAM Dokumentation des ITAM. IT Asset Management. Sie stammen aus verschiedenen Confluence Seiten die mit der Export funktion als PDF exportiert wurden.`

| # | Dateiname |
|---|-----------|
| 1 | Business+Capability.pdf |
| 2 | Digital+Solution.pdf |
| 3 | Fact+Sheet+Modeling+Guidelines.pdf |
| 4 | IT+Component.pdf |
| 5 | IT+Product.pdf |
| 6 | Initiative.pdf |
| 7 | Interface.pdf |
| 8 | Modeling+a+Business+Capability.pdf |
| 9 | Modeling+a+Business+Process.pdf |
| 10 | Modeling+an+IT+Component.pdf |
| 11 | Modeling+an+IT+Product.pdf |
| 12 | Modeling+an+Interface.pdf |
| 13 | Modeling+an+Organization.pdf |
| 14 | Modeling+of+a+Vendor.pdf |
| 15 | Modelling+Digital+Solution.pdf |
| 16 | Modelling+Initiative.pdf |
| 17 | Modelling+Objective.pdf |
| 18 | Objective.pdf |
| 19 | Organization.pdf |
| 20 | Process.pdf |
| 21 | Tech+Capability.pdf |
| 22 | Vendor.pdf |

### 4.2 Gold-Datei: `leanix_ontology_tripel_cleaned.txt`

**Pfad:** `datasets/intern/gold/leanix_ontology_tripel_cleaned.txt`

- **Format:** Eine einzige Zeile mit einer Python-Liste von Listen: `[['Subjekt', 'Prädikat', 'Objekt'], ...]`
- **Exakte Tripel-Anzahl: 936** (nicht 934 – Korrektur!)
- **Einzigartige Prädikate: 30**

Die 30 Prädikate:

```
affects, Child, classifies, consists_of, consumes, defines, ensures,
governed_by, improves, informs, is_similar_to, owned_by, Parent,
Predecessor, protects, provides, realizes, regulates, RequiredBy,
Requires, requires, responsible_for, status_of, Successor, supported_by,
supports, TechPlatform, transmits, uses, versioned_as
```

### 4.3 Weitere Gold-Dateien im Ordner

- `leanix_ontology.ttl` – OWL/TTL-Ontologie
- `leanix_ontology_cleaned.ttl` – bereinigte TTL-Version
- `leanix_ontology_classes.jsonl` – Klassen
- `leanix_ontology_tripel.txt` – unbereinigte Tripel
- `leanix_relation_definitions_from_ttl.json` – Relation Definitionen aus TTL

---

## 5. Evaluationsskript-Logik

**Hauptskript:** `evaluate/two_track_evaluation.py`  
`evaluate/evaluate_ontology_compliance.py` ist nur ein Forwarding-Wrapper auf `two_track_evaluation.py`.

### 5.1 Alignment-Methode

**Kein Embedding-Modell im Evaluationsskript.** Der semantische Abgleich verwendet:

- **Entity-Similarity:** `SequenceMatcher` (difflib) + Token-Jaccard (Wort-Überlappung), Maximum der beiden Werte.
- **Relation-Similarity:** Über ein extern bereitgestelltes `alignment_json` (vorberechnete Ähnlichkeiten, z. B. aus dem Schema-Retriever-E5-Modell). Ohne Alignment-JSON nur exaktes Matching.

**Thresholds:**
- `relation_threshold = 0.85` ✓ bestätigt (Default in `argparse`)
- `entity_threshold = 0.85` ✓ bestätigt (Default in `argparse`)

**Reihenfolge:**
1. **Exakt-Match zuerst:** Normalisierte Labels werden verglichen (casefold, Sonderzeichen-Entfernung, CamelCase-Split). Bei exaktem Match → Score 1.0.
2. **Dann Semantik-Match:** Für Relations über das Alignment-Index (mit `≥ relation_threshold`), für Entities über SequenceMatcher/Jaccard (mit `≥ entity_threshold`).
3. **Greedy Best-Match:** Alle Kanten (Pred→Gold) werden nach Overall-Score absteigend sortiert, dann greedy 1:1 zugewiesen (kein Hungarian, sondern greedy).

### 5.2 Ontologie-Compliance

#### `relation_valid_rate`

Die Liste gültiger Relationen kommt aus der **Gold-Ontologie-Datei** (`--reference`, typischerweise `leanix_ontology_tripel_cleaned.txt`). Es wird `gold_relations_norm = {normalize_label(t[1]) for t in ontology_triples}` berechnet – d. h. alle normalisierten Prädikate aus den Gold-Tripeln. **Nicht** aus `example_schema.csv`, nicht hardcoded, nicht aus OWL/TTL direkt.

#### `domain_valid_rate` / `range_valid_rate`

Domain/Range-Constraints werden **direkt aus den Gold-Tripeln abgeleitet:**

```python
for subj, rel, obj in ontology_triples:
    relation_domains_norm[normalize_label(rel)].add(normalize_label(subj))
    relation_ranges_norm[normalize_label(rel)].add(normalize_label(obj))
```

D. h.: Für jede Relation ist die Menge aller Subjekte, die in den Gold-Tripeln mit dieser Relation vorkommen, die gültige Domain; analog für Range. Es ist ein **closed-world assumption auf Basis der Gold-Daten**, keine externe OWL-Definition.

#### Vollständige Domain/Range-Definitionen

Die Definitionen sind zu umfangreich zum Inline-Auflisten (936 Tripel, 30 Prädikate, viele Domain/Range-Kombinationen). Sie entsprechen exakt den Subjekt/Objekt-Kombinationen in der Gold-Datei:

**Quelldatei:** `datasets/intern/gold/leanix_ontology_tripel_cleaned.txt`

Beispiel für `supports`:
- **Domain:** Digital Solution, IT Product, Initiative, Objective, Tech Platform
- **Range:** ADR, Application, Business Capability, Digital Solution, IT Product, Initiative, Objective, Process

### 5.3 Manuelle Enrichment-Evaluation

- **Stichprobengröße:** `sample_size = 50` , konfigurierbar via `--sample_size`
- **Stratifizierte Stichprobe:**
  - 50 % aus Stratum A: `unknown_relation` / nicht-alignbare Relationen
  - 50 % aus Stratum B: Domain/Range-Verletzungen
  - Rest auffüllend aus verbleibendem Pool
- **Bewertung:** **Durch Mensch.** Das Skript exportiert eine CSV-Datei (`novel_sample_for_manual_review.csv`) mit leerer `human_label`-Spalte zum manuellen Ausfüllen.
- **Bewertungskategorien:** `SUPPORTED` / `UNSUPPORTED` (binär). Es wird dann berechnet:
  - `enrichment_precision = SUPPORTED / total_labeled`
  - `enrichment_precision_strict = SUPPORTED / (SUPPORTED + UNSUPPORTED)`
- **Kein LLM-assistiertes Labeling** – rein manuell über CSV-Roundtrip.

---

## 6. Pipeline-Trichter – `all_combined_prompt2_with_filter/iter0`

**Quelle:** `output/all_combined_prompt2_with_filter/iter0/result_at_each_stage.json`

| Schritt | Tripel-Anzahl | Anmerkung |
|---------|---------------|-----------|
| OIE (roh) | **860** | Aus 409 Chunks |
| Schema Canonicalization | **860** | Bei `disable_dc=True`: 1:1 Durchreichung |
| Vor TU-Filter | **860** | Identisch mit OIE (keine Zwischenfilterung) |
| **Nach TU-Filter** | **717** | 143 Tripel entfernt (≈ 16,6 %) |
| `useful_kg.txt` (pre-dedup) | **951** | (409 Zeilen; manche Zeilen mit mehreren Tripeln) |
| **`useful_kg_dedup.txt` (final)** | **787** | 164 Duplikate entfernt |

> **Hinweis:** Es existiert kein `canon_kg_dedup.txt` in diesem Verzeichnis. `canon_kg.txt` enthält 1092 Tripel (409 Zeilen) – dies sind die Tripel vor dem TU-Filter mit Kanonisierungsversuch.

> **Diskrepanz:** Die 717 aus `result_at_each_stage.json` (Summe der `useful_triplets` pro Chunk) vs. 951 in `useful_kg.txt` deutet darauf hin, dass die Aggregationslogik beim Schreiben der `.txt`-Datei leicht abweicht (möglicherweise werden leere Listen anders behandelt oder multi-line-Tripel anders gezählt).

---

## Zusammenfassung der kritischen Befunde

1. **Few-Shot Iter 0 = WebNLG-generisch**, nicht LeanIX-spezifisch. Erst ab Iter 1 (Schema-Level-Prompt) werden domänenspezifische Beispiele genutzt.
2. **`example_schema.csv` ist NICHT die LeanIX-Ontologie** – es enthält 9 generische Wikidata-Relationen. Bei `disable_dc=True` irrelevant.
3. **`enrich_schema` ist im aktuellen Setup ein No-op** wegen `disable_dc=True`.
4. **Gold-Referenz: 936 Tripel** (nicht 934), 30 einzigartige Prädikate.
5. **Evaluation nutzt kein Embedding-Modell** – Entity-Ähnlichkeit wird über SequenceMatcher/Jaccard berechnet; Relations-Alignment ist optional/extern.
6. **Domain/Range-Constraints: geschlossene Welt** aus Gold-Tripeln, keine externe Ontologie-Definition.
