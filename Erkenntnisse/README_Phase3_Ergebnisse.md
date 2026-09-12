# Phase 3 — Hypothesen-Bibliothek: Zwischenstand

**Ziel:** Ein wiederverwendbares Test-Framework (`run_hypothesis_test`) bauen, das jede Markt-Hypothese nach demselben Muster prüft (Effektgröße, Trefferquote, Signifikanz), und damit mehrere bekannte Finanzmarkt-Anomalien am eigenen Datensatz testen.

## Methodik

- Basis: das bereinigte, split-adjustierte, liquide Universum aus Phase 2 (4.815 Ticker), zusätzlich winsorized (0,5/99,5-Perzentil) auf Forward-Return-Ebene.
- Jede Hypothese vergleicht eine Signal-Gruppe gegen die Baseline (alle Tage) via Welch-t-Test.
- Kontrollgruppen-Prüfung, wo nötig (siehe Hypothese 1), um triviale Erklärungen auszuschließen.
- Multiple-Testing-Bewusstsein bei Hypothese 4 (5 gleichzeitige Tests → Bonferroni-Schwelle 0,01 statt 0,05).

## Ergebnisse im Überblick

| # | Hypothese | Stärke des Belegs | Kernbefund |
|---|---|---|---|
| 1 | Gap-Reversal/Momentum | **Stark** (kontrollgruppen-geprüft) | Gaps (beide Richtungen) zeigen nach 20 Tagen deutliche Outperformance (+1,6 bis +2,2 Prozentpunkte ggü. Baseline); Kontrollgruppe (hohe Vola, kein Gap) zeigt nur +0,09pp — der Effekt ist gap-spezifisch, kein reiner Volatilitäts-Artefakt |
| 2 | 12-1-Momentum | **Solide, asymmetrisch** | Momentum-Gewinner (Top 20%) outperformen konsistent auf allen Horizonten (+0,03 bis +0,42pp, wachsend mit Zeit). Momentum-Verlierer underperformen nur kurzfristig; nach 20 Tagen kein Unterschied mehr zur Baseline (p=0,20) |
| 3 | Volatilitäts-Clustering | **Sehr stark** | Robustester Fund der Bibliothek: hohe Trailing-Vola führt zu ~1,8-2x höherer Forward-Vola; niedrige Trailing-Vola zu ~50% niedrigerer Forward-Vola. Praktisch relevant für künftiges Risikomanagement (Teil 2 des Projekts) |
| 4 | Wochentags-Effekt | **Schwach** | Kein klassischer Montags-Effekt (p>0,19). Donnerstag zeigt einen kleinen, aber signifikanten negativen Effekt (-0,085pp, p=0,000027, übersteht Bonferroni-Korrektur) — statistisch real, aber ökonomisch klein, vermutlich nach Transaktionskosten nicht handelbar |

## Wichtige methodische Lektion: Signifikanz ≠ Relevanz

Bei Stichprobengrößen von über einer Million Events wird praktisch jede noch so kleine Abweichung "statistisch signifikant" (siehe Kontrollgruppe in Hypothese 1: p=0,0004 bei einem Effekt von nur -0,01 Prozentpunkten). Ab dieser Phase wird für jede Hypothese neben dem p-Wert immer auch die Effektgröße (`differenz`-Spalte) bewertet — das Framework gibt beide standardmäßig aus.

## Datenprodukt

Alle Ergebnisse zusätzlich als durchsuchbare Tabelle gespeichert: `data/phase3_hypothesis_results.csv` (12 Zeilen: 4 Hypothesen × je 2-3 Signal-Richtungen × Zeithorizonte, exkl. Wochentags-Test mit eigener Struktur).

## Wiederverwendbare Bausteine (`src/data_loader.py`)

Neu in Phase 3: `run_hypothesis_test` (generisches Test-Framework, funktioniert für Renditen UND Volatilität via `metrik_praefix`), `add_gap_signal`, `add_volatility_control_signal`, `add_momentum_signal`, `add_forward_volatility_universe`, `add_volatility_regime_signal`, `test_weekday_effect`.

## Nächste Schritte (offen)

- Weitere Hypothesen möglich (z. B. saisonale Monats-Effekte, Post-Earnings-Drift falls Fundamentaldaten verfügbar werden)
- Transaktionskosten-bereinigte Backtests der stärksten Signale (Gap, Momentum, Vola-Clustering) — Übergang zu Teil 2 (Trading-Bot)
- Kombination mehrerer Signale (z. B. Momentum + niedrige Vola als Filter) als nächster Verfeinerungsschritt
