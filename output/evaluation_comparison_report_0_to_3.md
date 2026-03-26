# Vergleichsbericht der Evaluationsstände (0 -> 3)

## Kontext
Die Reports bilden aufeinanderfolgende Entwicklungsstände ab:
- **0.json (Baseline, all_combined2)**: Vor den beschriebenen Anpassungen.
- **1.json** (allcombined4): Erste Anpassung des OIE-Prompts.
- **2.json** (Allcombined5): Einführung des neuen Filterschritts (Fokus auf abstrakte Schema-Tripel).
- **3.json**(all_combined_prompt2_with_filter): Zusätzliche Verschärfung des OIE-Prompts.

## Executive Summary
Die Entwicklung zeigt eine klare Bewegung von sehr hoher Extraktionsmenge und starker semantischer Breite hin zu deutlich höherer Ontologie- und Schema-Konsistenz.

- **V0 -> V1**: Erste OIE-Anpassung reduziert etwas den Wildwuchs, aber bleibt ontologisch schwach.
- **V1 -> V2**: Starker Qualitätsgewinn bei Ontologie-Anbindung (v. a. Relationserkennung), dafür deutlicher Einbruch bei manuell bewerteter Enrichment-Qualität.
- **V2 -> V3**: Deutliche Stabilisierung durch strengeren Prompt; weniger Rauschen, bessere strukturelle Metriken und klare Erholung der manuellen Präzision.
- **Gesamt**: **V3** ist der beste Kompromiss zwischen Strenge, Schema-Nähe und praktischer Nutzbarkeit.

## Quantitativer Vergleich (Kernmetriken)

| Metrik | 0.json | 1.json | 2.json | 3.json | Interpretation |
|---|---:|---:|---:|---:|---|
| Prediction total | 2472 | 1509 | 1160 | 516 | Starker Rückgang, deutliche Ent-Rauschung |
| Novel count | 2457 | 1497 | 1126 | 485 | Ebenfalls stark reduziert |
| Novelty rate | 0.994 | 0.992 | 0.971 | 0.940 | Sinkt kontinuierlich (positiv) |
| Unique predicates total | 674 | 379 | 110 | 65 | Massive Fokussierung auf weniger Relationstypen |
| Unknown relation (invalid) | 2262 | 1299 | 212 | 101 | Sehr starke Verbesserung |
| Relation valid rate | 0.085 | 0.139 | 0.817 | 0.804 | Großer Sprung ab V2, in V3 stabil hoch |
| Domain valid rate | 0.009 | 0.023 | 0.163 | 0.238 | Kontinuierliche Verbesserung |
| Range valid rate | 0.009 | 0.013 | 0.078 | 0.134 | Kontinuierliche Verbesserung |
| Normalized exact precision | 0.005 | 0.008 | 0.028 | 0.058 | Kontinuierliche Verbesserung |
| Alignment matched | 15 | 12 | 34 | 31 | Ab V2 deutlich höher |
| Alignment recall | 0.0161 | 0.0128 | 0.0364 | 0.0332 | V2/V3 klar besser |
| Alignment F1 | 0.0313 | 0.0251 | 0.0648 | 0.0596 | Peak in V2, V3 nahe dran |
| Enrichment precision (manual) | 0.66 | 0.52 | 0.28 | 0.40 | Baseline am höchsten, V2-Einbruch, V3-Erholung |

## Entwicklungsanalyse pro Version

### Version 0 (Baseline, all_combined2)
- Extrem hohe Triple-Menge und sehr breite, teils deskriptive Prädikate (z. B. type, description, color, purpose).
- Sehr viele Unknown-Relation-Fälle und sehr geringe Ontologie-Validität.
- Überraschend hohe manuelle Enrichment-Präzision, aber stark vermischt mit nicht-schemahaften Aussagen.

**Fazit V0**: Hohe inhaltliche Breite, aber sehr geringe ontologische Steuerung.

### Version 1 (erste OIE-Anpassung)
- Sehr hohe Extraktionsbreite und große Prädikatsvielfalt.
- Viele Relationen außerhalb des Ontologie-Vokabulars.
- Sehr schwache Ontologie-Metriken.
- Gleichzeitig relativ hohe manuelle Enrichment-Präzision.

**Fazit V1**: Gegenüber V0 leicht konsolidiert, aber weiterhin ontologisch schwach.

### Version 2 (Filter für abstrakte Schema-Information)
- Zielwirkung klar sichtbar:
  - drastischer Rückgang unbekannter Relationen,
  - starke Verbesserung bei relation_valid_rate und Alignment.
- Neue Hauptproblematik:
  - hohe Zahl von Domain/Range-Verletzungen bei bekannten Relationen,
  - viele Tripel sind formal relationell näher an der Ontologie, aber argumentseitig unzulässig.
- Manuelle Enrichment-Präzision sinkt stark.

**Fazit V2**: Strategisch richtiger Schritt, aber mit starker Nebenwirkung auf inhaltliche Trefferqualität.

### Version 3 (strengerer OIE-Prompt)
- Noch stärkere Reduktion von Rauschen (halbierte Triple-Anzahl ggü. V2).
- Weitere Verbesserung von Domain/Range und normalized exact precision.
- Unknown relations nochmals reduziert.
- Manuelle Enrichment-Präzision erholt sich deutlich gegenüber V2.
- Alignment bleibt stark gegenüber V1 (auch wenn F1 knapp unter V2 liegt).

**Fazit V3**: Beste Balance aus Strenge, Schema-Fokus und praktischer Qualität.

## Fehlerstruktur und Systemverhalten

### Positiv
- Durchgängiger Rückgang nicht-ontologischer Relationen und Prädikatswildwuchs von V0 nach V3.
- Höhere Ontologie-Treue über fast alle strukturellen Metriken hinweg.

### Verbleibende Kernschwäche
- Der dominante Fehler verschiebt sich auf **Argumenttypisierung** (Subjekt/Objekt nicht im erlaubten Domain-/Range-Raum), nicht mehr primär auf Relationsnamen.

### Interpretation der Trade-offs
- Striktere Steuerung reduziert Rauschen und hebt formale Qualität.
- Zu aggressive Einschränkung kann semantische Neuheit und manuell wahrgenommene Nützlichkeit drücken (sichtbar in V2).
- V3 zeigt, dass Prompt-Strenge diesen Zielkonflikt besser ausbalanciert als V2.
- Die sehr hohe manuelle Präzision in V0/V1 ist vor dem Hintergrund geringer Ontologie-Konsistenz zu interpretieren (mehr freie, teils textnahe Aussagen statt strikt schemahafter Tripel).

## Gesamtbewertung
Wenn das primäre Ziel **abstrakte, ontologienahe Schema-Tripel** sind, ist die Entwicklung von V0 nach V3 **eindeutig positiv** und V3 der aktuell beste Stand.

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
Erstellt auf Basis der Dateien 0.json (all_combined2), 1.json, 2.json, 3.json.