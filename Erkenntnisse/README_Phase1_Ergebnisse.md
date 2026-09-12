# Phase 1 — Single-Stock Baseline: Ergebnisse

**Ziel:** Den kompletten Forschungszyklus einmal an einer Aktie (AAPL, 2016–2026) durchlaufen — laden, bereinigen, Hypothese testen, Robustheit prüfen.

## Datenpipeline
1. **Laden:** 610 Parquet-Dateien nach Ticker gefiltert (Predicate Pushdown), zu einer Zeitreihe zusammengeführt → 2.514 Handelstage.
2. **Deduplizieren:** Pro (Ticker, Tag) wird bei Konflikten die Zeile mit den meisten `transactions` behalten (validiert über 6 Stichproben-Dateien, 2016–2022, jeweils 100% sauber).
3. **Split-Adjustierung:** Automatische Erkennung von Kurssprüngen, die zu bekannten Split-Verhältnissen (2:1, 3:1, 4:1 ...) passen, danach rückwirkendes Back-Adjustment. Fand korrekt den AAPL 4:1-Split vom 31.08.2020 (einziger Split im Datenzeitraum), keine Fehlklassifikation über 2.514 Tage.
4. **Tägliche Renditen** aus adjustierten Schlusskursen.

## Hypothese
*"Führen außergewöhnliche Tagesbewegungen (>2 Std.-Abw.) bei AAPL zu Momentum oder Mean-Reversion in den Folgetagen?"*

## Ergebnis

| Zeitraum danach | Nach positivem Ausreißer | Baseline | p-Wert |
|---|---|---|---|
| 1 Tag | −0,90% | +0,12% | **0,007** |
| 5 Tage | −1,44% | +0,58% | **0,012** |
| 20 Tage | +0,40% | +2,33% | 0,122 |

Auf den ersten Blick: signifikante kurzfristige Mean-Reversion nach starken Gewinntagen (n=56).

## Robustheitscheck — der eigentliche Befund

Cluster-Analyse zeigte: 26,4% der Ausreißertage lagen ≤3 Tage auseinander (deutlich mehr als bei Zufallsverteilung zu erwarten) — Hinweis auf Häufung während des Corona-Crashs (Feb–Apr 2020).

Nach Ausschluss dieses Zeitfensters (n=62 statt 56):

| Zeitraum danach | Durchschnitt | p-Wert |
|---|---|---|
| 1 Tag | −0,22% | 0,242 |
| 5 Tage | −0,26% | 0,164 |

**Der Effekt ist statistisch nicht mehr signifikant.** Das ursprüngliche Signal war größtenteils ein Artefakt der Marktvolatilität im März 2020, kein robustes, wiederkehrendes Verhaltensmuster.

## Kernerkenntnis
Ein einzelnes Krisenereignis kann bei kleinen Stichproben (n<100) ein Signal erzeugen, das bei genauerer Prüfung nicht standhält. Das ist der methodische Hauptgrund, in Phase 2 auf viele Ticker gleichzeitig zu skalieren: größere, weniger cluster-anfällige Stichproben ermöglichen es, echte von zufälligen Mustern zu unterscheiden.

## Wiederverwendbare Bausteine (`src/data_loader.py`)
`find_parquet_files`, `load_parquet_file`, `deduplicate_daily_rows`, `load_ticker_history`, `adjust_for_splits`, `add_daily_returns`, `add_outlier_flag`, `event_study`, `teste_signifikanz` — bilden zusammen das Grundgerüst für Phase 2 und Phase 3.
