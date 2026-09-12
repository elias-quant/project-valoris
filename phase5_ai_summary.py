import requests
import pandas as pd
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELL = "llama3.1:8b"

VOLATILITAETS_HYPOTHESEN = {
    "Vola hoch (Top 20%)",
    "Vola tief (Bottom 20%)",
}

VERBOTENE_PROGNOSE_WOERTER = [
    "potenzial für", "könnte in der zukunft", "fundierte entscheidung",
    "empfehl", "sollte kaufen", "sollte verkaufen", "wiederkehren",
]

ERFUNDENE_BEGRIFFE = ["standardabweichung", "wahrscheinlichkeit von über", "handelsstrategie"]


def frage_ollama(prompt):
    antwort = requests.post(
        OLLAMA_URL,
        json={"model": MODELL, "prompt": prompt, "stream": False},
    )
    antwort.raise_for_status()
    return antwort.json()["response"]


def baue_kernsatz(zeile, hypothese_name):
    ist_vola = hypothese_name in VOLATILITAETS_HYPOTHESEN
    metrik = "die künftige Kursschwankung (Volatilität)" if ist_vola else "die künftige Rendite"

    if zeile["differenz"] > 0:
        richtung = "höher"
    elif zeile["differenz"] < 0:
        richtung = "niedriger"
    else:
        richtung = "gleich"

    signifikanz = "statistisch signifikant" if zeile["p_wert"] < 0.05 else "statistisch NICHT signifikant"

    return (
        f"Nach {zeile['horizont']} war {metrik} bei diesem Signal im Schnitt {richtung} "
        f"als der Durchschnitt aller Fälle (Signal: {zeile['durchschnitt_signal']:.4%}, "
        f"Baseline: {zeile['durchschnitt_baseline']:.4%}, Unterschied: {zeile['differenz']:.4%}), "
        f"und dieser Unterschied ist {signifikanz} (n={zeile['n_events']:,})."
    )


def baue_prompt(hypothese_name, kernsaetze):
    saetze_text = "\n".join(f"- {s}" for s in kernsaetze)
    return f"""Die folgenden Sätze sind bereits vollständig korrekt und enthalten alle
nötigen Informationen. Formuliere sie zu einem kurzen, natürlich klingenden
Absatz (max. 4 Sätze) um, OHNE die Bedeutung, Richtung, Zahlen, Zeiträume oder
Signifikanz-Aussagen zu verändern. Erwähne für JEDEN Zeitraum explizit, ob
der Unterschied signifikant war oder nicht. Füge NICHTS hinzu, was nicht in
den Sätzen steht (keine Handelsempfehlung, keine Kursprognose, keine
Aussage über die Zukunft). Antworte NUR mit dem umformulierten Absatz.

Hypothese: {hypothese_name}

{saetze_text}"""


def pruefe_antwort(hypothese_name, kernsaetze, ki_text):
    warnungen = []
    text_klein = ki_text.lower()

    ist_vola = hypothese_name in VOLATILITAETS_HYPOTHESEN
    if ist_vola and "volumen" in text_klein:
        warnungen.append("Verwechslung Volatilität/Handelsvolumen vermutet")

    kernsaetze_klein = " ".join(kernsaetze).lower()

    for begriff in ERFUNDENE_BEGRIFFE:
        if begriff in text_klein and begriff not in kernsaetze_klein:
            warnungen.append(f"Möglicherweise erfundener Begriff: '{begriff}'")

    for begriff in VERBOTENE_PROGNOSE_WOERTER:
        if begriff in text_klein:
            warnungen.append(f"Verbotene Prognose-/Empfehlungssprache: '{begriff}'")

    return warnungen


def main():
    pfad = Path("data") / "phase3_hypothesis_results.csv"
    df = pd.read_csv(pfad)

    print("=== Project Valoris — Phase 5: KI-Analyse-Assistent ===")
    print()

    for hypothese in df["hypothese"].unique():
        teil = df[df["hypothese"] == hypothese]
        kernsaetze = [baue_kernsatz(z, hypothese) for _, z in teil.iterrows()]

        print(f"--- {hypothese} ---")
        print("(Vorberechnete Kernsätze:)")
        for s in kernsaetze:
            print(" -", s)
        print()

        prompt = baue_prompt(hypothese, kernsaetze)
        erklaerung = frage_ollama(prompt)
        print("KI-Umformulierung:", erklaerung.strip())

        warnungen = pruefe_antwort(hypothese, kernsaetze, erklaerung)
        if warnungen:
            print("⚠️  AUTOMATISCHE WARNUNG(EN):")
            for w in warnungen:
                print("   -", w)

        print()
        print()


if __name__ == "__main__":
    main()