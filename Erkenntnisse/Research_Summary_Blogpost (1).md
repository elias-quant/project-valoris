# Was passiert wirklich, wenn eine Aktie stark ausschlägt? Eine 13-Millionen-Zeilen-Recherche

Ich wollte wissen, ob sich handfeste, wiederkehrende Muster in Aktienkursen finden lassen — nicht durch Bauchgefühl oder YouTube-Tipps, sondern durch systematisches, statistisch abgesichertes Testen. Also habe ich mir zehn Jahre Tagesdaten von über 10.000 US-Aktien besorgt und eine eigene Research-Pipeline gebaut, von null.

## Der erste Rückschlag war die wichtigste Lektion

Mein erster Test: Wenn Apple an einem Tag ungewöhnlich stark steigt oder fällt — was passiert danach? Das Ergebnis sah zunächst vielversprechend aus: ein klares Muster, statistisch signifikant. Aber als ich genauer hinschaute, entpuppte sich der Effekt fast komplett als Artefakt des Corona-Crashs im März 2020 — ein einzelnes Ereignis hatte das gesamte Bild verzerrt.

Das war frustrierend, aber genau der Punkt: **Eine einzelne Aktie liefert zu wenige Datenpunkte, um echte Muster von Zufall zu unterscheiden.** Also skalierte ich das gesamte Setup auf das komplette Marktuniversum — über 13 Millionen Zeilen, 10.663 Ticker.

## Datenqualität ist die eigentliche Arbeit

Was ich unterschätzt hatte: Der Großteil der Zeit floss nicht in Statistik, sondern in Datenbereinigung. Ein paar Beispiele, die ich unterwegs gefunden und gelöst habe:

- **Duplikate mit widersprüchlichen Werten** in denselben Tagesdaten — gelöst durch eine Regel (die Zeile mit den meisten Transaktionen gewinnt), die ich an mehreren Stichproben über sechs Jahre hinweg validiert habe.
- **Ein einzelner Aktien-Split**, der bei falscher Erkennung eine ganze Kurshistorie kaskadenartig falsch skalierte — behoben durch eine Kombination aus Kurs- UND Volumensprung als Bestätigungskriterium.
- **Ein Datenanbieter-Fehler bei Netgear**, wo der Kurs innerhalb weniger Tage zwischen 20 Cent und 77 Dollar hin- und hersprang. Keine der beiden Zahlen war ein Tippfehler — es war ein isolierter Datenfeed-Glitch, den ich über einen rollierenden Median-Vergleich systematisch abfangen konnte.
- **Eine stillschweigend fehlgeschlagene Datenintegration**, bei der 76% aller offiziellen Split-Daten beim Zusammenführen verloren gingen, weil der Verknüpfungsschlüssel (FIGI) bei den meisten Aktien schlicht fehlte — nur durch systematisches Nachrechnen an einem bekannten Referenzfall entdeckt.

Jeder dieser Fehler hätte unentdeckt in die finalen Ergebnisse einfließen können. Keiner davon war offensichtlich, bis ich gezielt nachgerechnet habe.

## Was am Ende stehen blieb

Mit sauberen Daten, Kontrollgruppen und über 145.000 Testfällen pro Hypothese zeigten sich mehrere robuste Muster:

- Aktien mit großen Kurslücken (Gaps) tendieren dazu, die Bewegung über die folgenden Wochen fortzusetzen — und das ist kein reiner Volatilitäts-Effekt, wie eine Kontrollgruppe bestätigte.
- Momentum-Gewinner outperformen konsistent; interessanterweise verschwindet der Effekt bei Momentum-Verlierern nach etwa einem Monat fast vollständig — ein asymmetrisches Muster.
- Volatilität ist ansteckend: Auf volatile Phasen folgen mit hoher statistischer Sicherheit weitere volatile Phasen.
- Der klassische "Ex-Dividende"-Kursrückgang bestätigte sich fast lehrbuchgenau — der Kurs fällt am Tag der Dividendenzahlung fast exakt um die Dividendenhöhe.

## Auch KI musste sich beweisen, nicht nur behauptet werden

Zum Schluss habe ich getestet, ob ein kleines, lokal laufendes KI-Modell die Ergebnisse in verständlicher Sprache zusammenfassen kann — ausdrücklich nur als Erklär-Werkzeug, nie als eigenständiger Analyst. Der erste Versuch (ein kompaktes 3-Milliarden-Parameter-Modell) produzierte dabei mehrfach faktisch falsche Aussagen — vertauschte Vorzeichen, erfundene Fachbegriffe, sogar eine verbotene "Kaufempfehlung", obwohl ausdrücklich untersagt. Ein größeres Modell (8B) war deutlich zuverlässiger, aber auch hier läuft jede Ausgabe durch einen automatischen Prüfmechanismus, der verdächtige Muster markiert — KI als geprüfter Assistent, nicht als Blackbox.

## Was als Nächstes kommt

Die validierten Signale werden jetzt zur Basis für ein Backtesting-System mit realistischen Transaktionskosten und striktem Risikomanagement — der nächste Schritt vom "was zeigt die Vergangenheit" zu "was ist damit heute noch sinnvoll umsetzbar".

Der vollständige Code, alle Zwischenschritte und jede gefundene Fehlerquelle sind dokumentiert im [GitHub-Repository](#).
