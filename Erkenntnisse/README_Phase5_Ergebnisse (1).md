# Phase 5 — Lokaler KI-Analyse-Assistent: Ergebnisse

**Ziel:** Ollama mit einem kleinen, lokalen Sprachmodell als reinen Erklär-Assistenten für die Hypothesen-Ergebnisse aus Phase 3 einsetzen — explizit kein Blackbox-Predictor, keine Kursprognose.

## Setup

Ollama lokal installiert, läuft als Hintergrunddienst (`ollama serve`) auf `localhost:11434`. Kein dediziertes VRAM auf der Zielhardware (Intel-Integrated-Grafik) — reine CPU-Inferenz.

## Iterativer Prozess: von unbrauchbar zu belastbar

**Runde 1 (Llama 3.2 3B, freie Interpretation):** Modell durfte Rohzahlen selbst interpretieren und umrechnen. Ergebnis: mehrere Zehnerpotenz-Fehler (z. B. 0,28 Prozentpunkte → "0,280%" fälschlich als 28% dargestellt in der Prosa), eine faktisch verdrehte Schlussfolgerung (Signifikanz bei falschem Zeithorizont behauptet), Verwechslung von Stichprobengröße mit Renditekennzahl.

**Runde 2 (Llama 3.2 3B, vorformatierte Kernsätze):** Python berechnet Richtung/Signifikanz/Prozentwerte korrekt vor, Modell soll nur noch umformulieren. Zahlenfehler verschwanden, aber neue Fehlerklasse: Verwechslung von "nicht signifikant" mit "nicht vorhanden", wiederholte Verwechslung von Volatilität mit Handelsvolumen (obwohl im Text explizit "Volatilität" vorgegeben), erfundene Fachbegriffe ("Standardabweichung" ohne Grundlage), unerlaubte Zukunftsprognosen ("Potenzial für zukünftige Gewinne").

**Runde 3 (Llama 3.1 8B, vorformatierte Kernsätze + automatischer Prüf-Mechanismus):** Deutlich verbesserte Treue — 6 von 7 getesteten Hypothesen fehlerfrei wiedergegeben (Richtung, exakte Werte, Signifikanz pro Zeithorizont, keine Zukunftsaussagen). Der verbleibende Fehler im letzten Testlauf war kein Modellfehler, sondern ein eigener Bug in der Vorverarbeitung (siehe unten).

## Automatischer Prüf-Mechanismus (`pruefe_antwort`)

Statt dem Modell blind zu vertrauen, scannt eine Python-Funktion jede Antwort automatisch auf bekannte Fehlermuster:
- Verwechslung Volatilität/Handelsvolumen
- Erfundene, nicht in den Ausgangsdaten vorkommende Fachbegriffe
- Verbotene Prognose-/Empfehlungssprache (z. B. "Potenzial für", "sollte kaufen")

Gibt Warnungen aus, statt Fehler stillschweigend durchzulassen — das Prinzip "KI nur als geprüfter Assistent, nicht als Blackbox" wird damit konkret umgesetzt, nicht nur behauptet.

## Eigener Bug entdeckt und korrigiert

Bei der Erweiterung des Volatilitäts-Sets wurde versehentlich "Kontrolle: hohe Vola, kein Gap" hinzugefügt — obwohl diese Hypothese Rendite misst, nicht Volatilität (der Name bezieht sich nur auf das Auswahlkriterium der Ticker). Das führte zu einer falschen Metrik-Bezeichnung in den Kernsätzen selbst, die das Modell danach treu (und korrekt) übernommen hat. Lehre: Der Prüf-Mechanismus schützt vor KI-Fehlern, aber nicht vor Fehlern in der eigenen Vorverarbeitung — beides muss geprüft werden.

## Kernerkenntnis

Ein 3B-Modell war für treue Wiedergabe quantitativer Ergebnisse ungeeignet, auch mit sorgfältigem Prompt-Engineering — das ist eine dokumentierte, reale Grenze kleiner LLMs, keine Frage der Formulierung. Ein 8B-Modell auf derselben Hardware (langsamer, aber machbar) liefert brauchbare Ergebnisse, sofern zusätzlich ein automatischer Konsistenz-Check vorgeschaltet wird. Die vorberechneten Kernsätze (100% korrekt, da direkt aus den Daten generiert) bleiben die maßgebliche Quelle; die KI-Umformulierung ist sprachlicher Feinschliff, kein Ersatz — jede Ausgabe sollte vor Weiterverwendung (README, Video) kurz gegengelesen werden.

## Wiederverwendbare Bausteine (`phase5_ai_summary.py`)

`baue_kernsatz` (korrekte Vorverarbeitung), `baue_prompt` (eng gefasster Umformulierungs-Auftrag), `pruefe_antwort` (automatischer Fidelity-Check) — als Muster für jeden künftigen Einsatz eines lokalen LLM im Projekt wiederverwendbar, z. B. für automatisierte Tages-Reports im Trading-Bot (Teil 2).
