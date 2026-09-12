# Project Valoris

Eine selbstgebaute quantitative Research Engine für US-Aktien (2016–2026): von roher Datenbeschaffung über systematische Bereinigung bis zu statistisch getesteten Markt-Hypothesen — mit jedem Fehler, jedem Umweg und jeder Korrektur offen dokumentiert.
*disclaimer : AI was used in helping with cleaning up code, making remarks to what which code does and for construction of part of the README's also AI itself is used in This project locally*

## Worum geht's

Kann ich mit öffentlich/kommerziell verfügbaren Marktdaten eigenständig eine belastbare, methodisch saubere Research-Pipeline bauen — von der Rohdatei bis zur getesteten Hypothese? Dieses Projekt ist die Antwort: 13,27 Millionen Zeilen Kursdaten über 10.663 Ticker, bereinigt, korrekt split-/dividenden-adjustiert, gegen bekannte Finanzmarkt-Anomalien getestet — inklusive eines lokalen KI-Assistenten, der die Ergebnisse in Klartext erklärt (mit eingebauter Fehlerprüfung, kein Blackbox-Vertrauen).

## Kernergebnisse auf einen Blick

| Hypothese | Befund | Stärke |
|---|---|---|
| Gap-Momentum | Kurslücken (>3%) zeigen nach 20 Tagen +1,6 bis +2,2 Prozentpunkte Outperformance, kontrollgruppen-geprüft (kein reines Volatilitäts-Artefakt) | Stark |
| 12-1-Momentum | Momentum-Gewinner outperformen konsistent über alle Horizonte; Verlierer-Underperformance verschwindet nach 20 Tagen (asymmetrischer Effekt) | Solide |
| Volatilitäts-Clustering | Robustester Fund: hohe Trailing-Volatilität führt zu ~2x höherer Forward-Volatilität | Sehr stark |
| Ex-Dividend-Drop | Kurs fällt am Ex-Tag fast exakt um die Dividendenhöhe (0,91% vs. 0,89% Dividendenrendite) — lehrbuchgenaue Bestätigung der Markteffizienz-Theorie | Sehr stark |
| Wochentags-Effekt | Kein klassischer Montags-Effekt mehr nachweisbar (marktbereinigt) | Schwach |

Alle Ergebnisse basieren auf über 145.000 Events pro Gruppe, statistisch getestet (Welch-t-Test), mit Kontrollgruppen und Winsorizing gegen Ausreißer-Verzerrung.

## Projektaufbau

```
Project Valoris/
├── src/
│   ├── data_loader.py       # Kern-Pipeline: Laden, Bereinigen, Split-Adjustierung, Event Study
│   └── preprocessing.py     # Corporate-Actions-Integration (Splits, Dividenden)
├── Erkenntnisse/
│   ├── phase 1,2,3
│   └──Alle Readme's (weiter verlinkt in diesem Reamde)
├── data/
│   └── phase 3 hypothesis results
├── main.py                  # Multi-Ticker-Universum + Corporate Actions
├── phase4b_total_return.py
├── phase5_ai_summary.py     # Lokaler KI-Analyse-Assistent (Ollama)

## Methodik in Kürze

1. **Daten:** 610 Parquet-Dateien (US-Aktien, Tagesdaten 2016–2026) → per DuckDB dedupliziert und konsolidiert
2. **Bereinigung:** Rollierende Median-Ausreißer-Erkennung, vektorisierte Split-Adjustierung, offizielle Corporate-Actions-Integration (nach Entdeckung mehrerer eigener Bugs, siehe Phase-4-README)
3. **Robustheits-Checks durchgehend:** Kontrollgruppen (z. B. Gap-Effekt gegen reine Volatilität getestet), Winsorizing gegen Ausreißer, Bonferroni-Korrektur bei Mehrfachtests, Survivorship-Bias-Audit (5,6% fehlende Delistings im relevanten Zeitfenster, dokumentiert)
4. **KI-Einsatz bewusst eingeschränkt:** Lokales LLM (Llama 3.1 8B via Ollama) nur zur Textzusammenfassung bereits berechneter Ergebnisse, nie zur eigenständigen Analyse — mit automatischem Konsistenz-Check gegen Fehlinterpretation

## Limitationen (ehrlich benannt)

- **Survivorship Bias:** ~5,6% der im Beobachtungszeitraum delisteten Common Stocks fehlen im Preisdatensatz — Ergebnisse tendenziell leicht optimistisch verzerrt.
- **Keine Optionsdaten:** Ursprünglich für Marktwarwartungs-Analyse via Optionen geplant, war nicht verfügbar; Phase 4 wurde stattdessen zu Corporate-Actions-Integration umgewidmet.
- **Kleine LLMs sind bei quantitativer Texttreue unzuverlässig:** Dokumentiert in Phase 5 — ein 3B-Modell wurde nach mehreren Fehlversuchen verworfen, 8B liefert brauchbare, aber weiterhin geprüfungsbedürftige Ergebnisse.
- **Keine Transaktionskosten:** Alle Ergebnisse sind Brutto-Signale, noch nicht auf reale Handelbarkeit geprüft (folgt in Teil 2).

## Setup (zum Nachvollziehen)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install pandas pyarrow duckdb scipy matplotlib requests
```

Erstelle eine lokale `key.py` (nicht im Repo, siehe `.gitignore`) mit:
```python
DATA_ROOT = r"Pfad\zu\deinen\Rohdaten"
DATA_ROOT_CORP_ACTIONS = r"Pfad\zu\Corporate-Actions-Daten"
```

Rohdaten sind nicht Teil dieses Repos (Lizenz-/Größenbeschränkungen). Struktur und Schema sind in den Phase-READMEs dokumentiert.

## Detaillierte Ergebnisse je Phase

- [Phase 1 — Single-Stock Baseline](README_Phase1_Ergebnisse.md)
- [Phase 2 — Multi-Ticker Universe](README_Phase2_Ergebnisse.md)
- [Phase 3 — Hypothesen-Bibliothek](README_Phase3_Ergebnisse.md)
- [Phase 4 — Corporate Actions & Survivorship-Bias-Audit](README_Phase4_Ergebnisse.md)
- [Phase 5 — Lokaler KI-Analyse-Assistent](README_Phase5_Ergebnisse.md)

## Ausblick

Teil 2 dieses Projekts (in Arbeit): ein Trading-Bot, der die hier validierten Signale mit Transaktionskosten-bereinigtem Backtesting, striktem Risikomanagement und optional TimesFM (Zeitreihen-Vorhersagemodell) kombiniert — erst Paper Trading, dann kontrollierter Live-Betrieb mit kleinem Kapital.

---

*Dieses Projekt ist ein persönliches Lernprojekt. Keine Anlageberatung, keine Gewährleistung für Richtigkeit oder zukünftige Handelbarkeit der gezeigten Muster.*

*Vielleicht ist Forschung der Versuch, aus dem, was geschehen ist, etwas über das zu lernen, was geschehen könnte. Und vielleicht ist Weisheit die Erkenntnis, dass zwischen beidem immer ein Rest bleibt, den kein Modell und keine Zahl überbrücken kann. - Elias Jan Emanuel*
