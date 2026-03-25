# Vergleichsbericht der drei Evaluationsstände (1 -> 3)

## Kontext
Die drei Reports bilden aufeinanderfolgende Entwicklungsstände ab:
- **1.json**: Erste Anpassung des OIE-Prompts.
- **2.json**: Einführung des neuen Filterschritts (Fokus auf abstrakte Schema-Tripel).
- **3.json**: Zusätzliche Verschärfung des OIE-Prompts.

## Executive Summary
Die Entwicklung zeigt eine klare Bewegung von hoher Extraktionsmenge und hoher semantischer Breite hin zu stärkerer Ontologie- und Schema-Konsistenz.

- **V1 -> V2**: Starker Qualitätsgewinn bei Ontologie-Anbindung (v. a. Relationserkennung), aber deutlicher Einbruch bei manuell bewerteter Enrichment-Qualität.
- **V2 -> V3**: Deutliche Stabilisierung durch strengeren Prompt; weniger Rauschen, bessere strukturelle Metriken und klare Erholung der manuellen Präzision.
- **Gesamt**: **V3** ist der beste Kompromiss zwischen Strenge, Schema-Nähe und praktischer Nutzbarkeit.

## Quantitativer Vergleich (Kernmetriken)

| Metrik | 1.json | 2.json | 3.json | Interpretation |
|---|---:|---:|---:|---|
| Prediction total | 1509 | 1160 | 516 | Starker Rückgang, deutliche Ent-Rauschung |
| Novel count | 1497 | 1126 | 485 | Ebenfalls stark reduziert |
| Novelty rate | 0.992 | 0.971 | 0.940 | Sinkt kontinuierlich (positiv) |
| Unique predicates total | 379 | 110 | 65 | Massive Fokussierung auf weniger Relationstypen |
| Unknown relation (invalid) | 1299 | 212 | 101 | Sehr starke Verbesserung |
| Relation valid rate | 0.139 | 0.817 | 0.804 | Großer Sprung ab V2, in V3 stabil hoch |
| Domain valid rate | 0.023 | 0.163 | 0.238 | Kontinuierliche Verbesserung |
| Range valid rate | 0.013 | 0.078 | 0.134 | Kontinuierliche Verbesserung |
| Normalized exact precision | 0.008 | 0.028 | 0.058 | Kontinuierliche Verbesserung |
| Alignment matched | 12 | 34 | 31 | Deutlich höher als V1 |
| Alignment recall | 0.0128 | 0.0364 | 0.0332 | V2/V3 klar besser als V1 |
| Alignment F1 | 0.0251 | 0.0648 | 0.0596 | V2 leicht vor V3 |
| Enrichment precision (manual) | 0.52 | 0.28 | 0.40 | V2-Einbruch, V3 erholt sich |

## Entwicklungsanalyse pro Version

### Version 1 (erste OIE-Anpassung)
- Sehr hohe Extraktionsbreite und große Prädikatsvielfalt.
- Viele Relationen außerhalb des Ontologie-Vokabulars.
- Sehr schwache Ontologie-Metriken.
- Gleichzeitig relativ hohe manuelle Enrichment-Präzision.

**Fazit V1**: Inhaltlich breit, aber ontologisch sehr unkontrolliert.

### Version 2 (Filter für abstrakte Schema-Information)
- Zielwirkung klar sichtbar:
  - drastischer Rückgang unbekannter Relationen,
  - starke Verbesserung bei relation_valid_rate und Alignment.
- Neue Hauptproblematik:
  - hohe Zahl von Domain/Range-Verletzungen bei bekannten Relationen,
  - viele Tripel sind formal relationell näher an der Ontologie, aber argumentseitig unzulässig.
- Manuelle Enrichment-Präzision sinkt stark.

**Fazit V2**: Richtiger strategischer Schritt, aber mit starker Nebenwirkung auf inhaltliche Trefferqualität.

### Version 3 (strengerer OIE-Prompt)
- Noch stärkere Reduktion von Rauschen (halbierte Triple-Anzahl ggü. V2).
- Weitere Verbesserung von Domain/Range und normalized exact precision.
- Unknown relations nochmals reduziert.
- Manuelle Enrichment-Präzision erholt sich deutlich gegenüber V2.
- Alignment bleibt stark gegenüber V1 (auch wenn F1 knapp unter V2 liegt).

**Fazit V3**: Beste Balance aus Strenge, Schema-Fokus und praktischer Qualität.

## Fehlerstruktur und Systemverhalten

### Positiv
- Übergang von freier Relationserfindung zu deutlich kontrollierterem Relationenset.
- Höhere Ontologie-Treue über fast alle strukturellen Metriken hinweg.

### Verbleibende Kernschwäche
- Der dominante Fehler verschiebt sich auf **Argumenttypisierung** (Subjekt/Objekt nicht im erlaubten Domain-/Range-Raum), nicht mehr primär auf Relationsnamen.

### Interpretation der Trade-offs
- Striktere Steuerung reduziert Rauschen und hebt formale Qualität.
- Zu aggressive Einschränkung kann jedoch semantische Neuheit und manuell wahrgenommene Nützlichkeit drücken.
- V3 zeigt, dass Prompt-Strenge diesen Zielkonflikt besser ausbalanciert als V2.

## Gesamtbewertung
Wenn das primäre Ziel **abstrakte, ontologienahe Schema-Tripel** sind, ist die Entwicklung **eindeutig positiv** und V3 der aktuell beste Stand.

Wenn das primäre Ziel **maximale Enrichment-Neuheit mit hoher manueller Support-Rate** ist, bleibt weiterer Feinschliff nötig.

## Empfehlungen für den nächsten Iterationsschritt
1. **Domain/Range-Gating nach Relationserkennung**:
   bekannte Relationen nur mit plausiblen Argumenttypen durchlassen (hart oder score-basiert).
2. **Relationsspezifische Prompt-Constraints**:
   pro Top-Relation erlaubte Subjekt-/Objektklassen explizit machen.
3. **Zwei-Ausgabe-Kanäle etablieren**:
   - Kanal A: streng schema-konform
   - Kanal B: explorative Novel-Facts
4. **Zusätzliche Effizienzmetrik tracken**:
   matched/prediction zur Fortschrittsmessung unter variierender Triple-Anzahl.

---
Erstellt auf Basis der Dateien 1.json, 2.json, 3.json.