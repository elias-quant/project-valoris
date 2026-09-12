# Phase 2 — Multi-Ticker Universe: Ergebnisse

**Ziel:** Dieselbe Event-Study-Hypothese aus Phase 1 (Mean-Reversion nach Ausreißertagen) über das gesamte US-Aktienuniversum testen (10.663 Ticker, 2016–2026), statt nur eine Aktie — um zu prüfen, ob sich ein robustes Marktmuster zeigt oder ob das Phase-1-Signal nur Zufall war.

## Datenpipeline (DuckDB + pandas)

1. **Konsolidierung:** 610 Rohdateien → 1 deduplizierter Datensatz (13.267.710 Zeilen, 10.663 Ticker), via DuckDB `ROW_NUMBER() OVER (PARTITION BY ticker, timestamp_open_utc ORDER BY transactions DESC)`. Gecacht in `data/clean_universe.parquet`.
2. **Preis-Ausreißer-Erkennung:** Rollierender Median (61-Tage-Fenster, zentriert) pro Ticker; Tage mit >5x Abweichung vom lokalen Median werden entfernt (3.537 Zeilen, 0,027%).
3. **Split-Adjustierung:** Wie in Phase 1, jetzt vektorisiert über alle Ticker gleichzeitig (kein `df.apply(axis=1)` mehr — das lief anfangs 2+ Stunden, siehe unten).
4. **Tägliche Renditen, Ausreißer-Flag (pro Ticker, 2 Std.-Abw.), Forward Returns (1/5/20 Tage).**
5. **Liquiditätsfilter:** Median-Kurs ≥ $5, Median-Dollar-Volumen ≥ $1 Mio. → 4.815 von 10.663 Tickern bleiben.
6. **Winsorizing:** Forward Returns auf das 0,5/99,5-Perzentil gekappt (nach dem Liquiditätsfilter, damit die Grenzen nicht selbst von Penny-Stocks verzerrt werden).

## Zentrale Debugging-Erkenntnisse

**Performance:** Eine erste Version der Split-Erkennung nutzte `df.apply(axis=1)` mit `.loc`-Lookups in der Zeilenschleife — bei 13,27 Mio. Zeilen lief das 2+ Stunden. Fix: vollständige Vektorisierung (Schleife nur über die 7 bekannten Split-Verhältnisse, `.shift()` statt `.loc`).

**Kaskadenfehler durch falsche Reihenfolge:** Ursprünglich lief Split-Adjustierung vor der Ausreißer-Erkennung. Ein einzelner Datenfehler (Bad Tick), der zufällig zu einem Split-Verhältnis passte, wurde fälschlich als echter Split erkannt — die *gesamte* Historie davor wurde dauerhaft falsch skaliert. Fix: Ausreißer-Erkennung läuft jetzt **vor** der Split-Adjustierung.

**Fallstudie NTGR (Netgear), Juli 2018:** Innerhalb weniger Tage wechselten die Rohdaten zwischen ~$0,20–0,37 und ~$76–78 — kein Split, sondern ein Datenanbieter-Fehler. Recherche ergab einen plausiblen Kontext (der spätere Arlo-Spin-off im August 2018 erklärt, warum unadjustierte Rohdaten höher liegen als heutige, rückwirkend bereinigte Charts), löst aber nicht das eigentliche Problem: Ein Kurs kann nicht tageweise zwischen $0,30 und $77 hin- und herspringen. Der rollierende Median (Fenster: ~3 Monate) filterte die kurze Fehler-Episode korrekt heraus, weil sie im breiteren Zeitfenster in der Minderheit war.

## Ergebnis: Event Study über das liquide Universum (n > 145.000 pro Gruppe)

| Zeitraum danach | Nach positivem Ausreißer | Nach negativem Ausreißer | Baseline (alle Tage) |
|---|---|---|---|
| 1 Tag | −0,08% (p<0,0001) | +0,30% (p<0,0001) | 0,05% |
| 5 Tage | +0,09% (p<0,0001) | +0,67% (p<0,0001) | 0,27% |
| 20 Tage | 2,71% (p<0,0001) | 3,66% (p<0,0001) | 1,12% |

**Interpretation:**
- Nach starken **positiven** Ausreißertagen: leichte, aber statistisch hochsignifikante Mean-Reversion — die Rendite bleibt unter der Baseline, besonders kurzfristig (1 Tag).
- Nach starken **negativen** Ausreißertagen: Rendite liegt konsistent *über* der Baseline auf allen drei Horizonten — Hinweis auf eine leichte Erholungstendenz nach Verlusttagen.
- Beide Effekte sind angesichts der riesigen Stichprobe (>145.000 Events je Gruppe) und durchgehend signifikanter p-Werte deutlich robuster als das Phase-1-Ergebnis bei AAPL allein, das den Robustheitscheck nicht überstand.

## Kernerkenntnis

Ein Signal, das bei einer einzelnen Aktie nicht standhielt (Phase 1), zeigt sich über das gesamte Marktuniversum als robust und statistisch signifikant. Das unterstreicht den methodischen Hauptpunkt aus Phase 1: **Stichprobengröße und Datenqualität entscheiden darüber, ob ein Muster echt oder Zufall ist.** Der Großteil des Aufwands in Phase 2 lag folgerichtig nicht im eigentlichen Test, sondern in der Datenbereinigung — mehrere Iterationen zur Erkennung von Duplikaten, Splits, isolierten Datenfehlern und Penny-Stock-Rauschen.

## Wiederverwendbare Bausteine (`src/data_loader.py`)

Neu in Phase 2: `save_clean_universe`, `load_clean_universe`, `flag_price_outliers_rolling`, `adjust_for_splits_universe`, `add_daily_returns_universe`, `add_outlier_flag_universe`, `add_forward_returns_universe`, `filter_liquid_universe`, `winsorize_column`, `event_study_universe` — bilden zusammen die Grundlage für Phase 3 (Hypothesen-Bibliothek), wo dieselbe Pipeline für weitere Hypothesen (Gap-Reversal, Momentum, Volatilitäts-Clustering) wiederverwendet wird.
