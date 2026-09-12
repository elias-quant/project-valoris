# Phase 4 — Corporate Actions Integration & Survivorship-Bias-Audit: Ergebnisse

**Ziel:** Ursprünglich für Optionsdaten vorgesehen — der Datenpartner hatte keine. Stattdessen: offizielle Split-/Dividendendaten und eine vollständige Company-Reference-Liste (inkl. delisteter Ticker) integrieren, um (a) unsere selbstgebaute, fehleranfällige Split-Schätzung durch exakte Daten zu ersetzen und (b) Survivorship Bias in Phase 2/3 zu quantifizieren.

## Datenquelle

Corporate-Actions-Paket eines Kollegen: `splits.csv` (26.922 Zeilen, 1978–2026), `dividends.csv` (707.908 Zeilen, 2000–2027), `company_reference.csv` (35.675 Ticker, davon 23.002 delistet — **ohne** Survivorship Bias, da explizit alle delisteten Ticker enthalten sind).

## Zentrale Debugging-Erkenntnisse

**Bug 1 — FIGI-Merge verwarf 76% aller Splits stillschweigend.** Die ursprüngliche Integration mergte Splits/Dividenden über FIGI, sobald die Spalte in beiden Tabellen existierte — unabhängig davon, ob sie gefüllt war. Da FIGI bei 76% der Splits und 48% der Dividenden fehlt (bei 79,6% aller Ticker mit Splits durchgehend), matchte der Merge dort nie. Fix: Merge-Key auf `ticker + date` umgestellt (wie vom Datenlieferanten explizit empfohlen). Ergebnis: Zeilen mit tatsächlich angewendeter Split-Adjustierung stieg von einem Bruchteil auf 1.747.859.

**Bug 2 — Doppelte Split-Adjustierung.** Die Corporate-Actions-Pipeline wurde versehentlich auf `universe_processed.parquet` angewendet — das war bereits durch unsere eigene (geschätzte) Split-Logik aus Phase 2 adjustiert. Ergebnis: Kurse vor Split-Tagen wurden zweimal geteilt (z. B. AAPL: $125 statt $500 als Ausgangsbasis). Fix: neuer Zwischen-Cache `universe_raw_deduped.parquet` — dedupliziert und von Preis-Ausreißern befreit, aber **vor** jeglicher Split-Adjustierung — als Grundlage für die offizielle Adjustierung.

**Bug 3 — Dividenden nicht split-adjustiert.** `div_amount` blieb auf Alt-Aktien-Basis, während `close_adj` bereits angepasst war (Inkonsistenz für künftige Total-Return-Berechnungen). Fix: `div_amount_adj = div_amount × historical_adjustment_factor`.

**Verifiziert, kein Bug:** Der `historical_adjustment_factor` ist bereits kumulativ vorberechnet (enthält bei Mehrfach-Splits automatisch alle nachfolgenden Split-Ereignisse) — ein einfaches `bfill()` pro Ticker reicht, keine manuelle Multiplikationskette nötig.

## Verifikation (AAPL, 4:1-Split 31.08.2020)

| Datum | close (roh) | close_adj | volume | volume_adj |
|---|---|---|---|---|
| 2020-08-27 | 500,04 | 125,01 | 38.830.783 | 155.323.132 |
| 2020-08-31 | 129,04 | 129,04 | 224.412.840 | 224.412.840 |

Dividende 07.08.2020: `div_amount = 0,82` (Alt-Basis), `div_amount_adj = 0,205` (Neu-Basis) — beide korrekt konsistent mit dem Split-Faktor 0,25.

## Survivorship-Bias-Audit

| Vergleich | Fehlende delistete Ticker |
|---|---|
| Alle Wertpapiertypen, alle Zeiträume | 78,8% |
| Nur Common Stocks, alle Zeiträume | 29,2% |
| Nur Common Stocks, **innerhalb 2016–2026** (unser Beobachtungsfenster) | **5,6%** |

Die ersten beiden Zahlen waren größtenteils Scope-Artefakte (andere Wertpapiertypen wie Warrants/ETFs; Delistings vor 2016, außerhalb unseres Datenfensters). Die relevante Zahl — delistete Common Stocks, die während unseres tatsächlichen Beobachtungszeitraums ausgeschieden sind — liegt bei **5,6% fehlend**. Das ist ein realer, aber kleiner Survivorship-Bias-Restfehler: Die Phase-2/3-Ergebnisse (Gap-Momentum, 12-1-Momentum, Vola-Clustering) sind dadurch tendenziell leicht optimistisch verzerrt, aber nicht grundlegend in Frage gestellt.

## Kernerkenntnis

Drei nicht-triviale Bugs traten erst durch systematisches Nachrechnen an einem bekannten Referenzfall (AAPL) zutage — keiner davon wäre ohne den "Fertig!"-Output sichtbar gewesen. Der Survivorship-Bias-Wert zeigt zudem, wie stark eine erste, unpräzise Messung (78,8%) in die Irre führen kann, bevor Scope und Zeitfenster korrekt eingegrenzt werden.

## Neue Datenprodukte

- `data/universe_raw_deduped.parquet` — bereinigt, dedupliziert, **nicht** split-adjustiert (Grundlage für offizielle Adjustierung)
- `data/universe_with_corporate_actions.parquet` — finales Panel mit `close_adj`, `volume_adj`, `div_amount`, `div_amount_adj`, `is_recurring`, `is_special_shock`, `is_unknown`

## Phase 4b — Total Return & Ex-Dividend-Drop

**Dividendenbeitrag zur Gesamtrendite:** +1,84% p.a. (Differenz Total Return vs. reine Kursrendite, hochgerechnet) — deckt sich mit dem historisch üblichen Bereich für den US-Markt (1,5–2,5% p.a.), guter Plausibilitätsbeleg für `div_amount_adj`.

**Ex-Dividend-Drop-Effekt:** Am Ex-Dividenden-Tag fällt der Kurs im Schnitt um 0,9094 Prozentpunkte stärker als an einem durchschnittlichen Tag (p≈0, n=64.084) — nahezu deckungsgleich mit der durchschnittlichen Dividendenrendite an diesen Tagen (0,8878%). Das bestätigt die Markteffizienz-Theorie fast lehrbuchgenau: Der Kurs korrigiert um ungefähr den Betrag, den ein Käufer ab dem Ex-Tag nicht mehr erhält.

*Methodische Einschränkung:* Vergleich erfolgt gegen die globale Baseline (alle Ticker, alle Tage), nicht gegen eine ticker-eigene Baseline — Dividenden-Zahler unterscheiden sich systematisch vom Durchschnitt (typischerweise größere, reifere Firmen). Angesichts der engen Übereinstimmung mit der theoretischen Erwartung vermutlich nur eine Nuance, keine grundsätzliche Änderung des Befunds.

## Nächste Schritte (offen)

- Übergang zu Phase 5 (lokaler Analyse-Assistent) und Phase 6 (Dokumentation/Portfolio-Reife)
- Übergang zu Teil 2 (Trading-Bot): Datenformat ist bereits kompatibel mit TimesFM (sauberes chronologisches Panel pro Ticker)
