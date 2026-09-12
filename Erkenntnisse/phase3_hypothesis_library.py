from pathlib import Path
import pandas as pd

from src.data_loader import (
    add_forward_returns_universe,
    filter_liquid_universe,
    winsorize_column,
    add_gap_signal,
    add_volatility_control_signal,
    add_momentum_signal,
    add_forward_volatility_universe,
    add_volatility_regime_signal,
    test_weekday_effect,
    run_hypothesis_test,
)


print("=== Project Valoris — Phase 3: Hypothesen-Bibliothek ===")
print()

# --- Basis laden (aus Phase-2-Cache) ---
verarbeitet_pfad = Path("data") / "universe_processed.parquet"
universum = pd.read_parquet(verarbeitet_pfad)
print("Geladen aus Cache:", len(universum), "Zeilen")
print()

# --- Liquides, winsorized Set (eigener Cache) ---
liquide_cache_pfad = Path("data") / "universe_liquide_winsorized.parquet"

if liquide_cache_pfad.exists():
    universum_liquide = pd.read_parquet(liquide_cache_pfad)
    print(f"Liquides Set aus Cache geladen: {liquide_cache_pfad}")
else:
    print("Kein Cache vorhanden, berechne neu...")
    universum = add_forward_returns_universe(universum)
    universum_liquide = filter_liquid_universe(universum)
    for spalte in ["fwd_1d", "fwd_5d", "fwd_20d"]:
        universum_liquide = winsorize_column(universum_liquide, spalte)
    universum_liquide.to_parquet(liquide_cache_pfad, index=False)
    print(f"Gespeichert: {liquide_cache_pfad}")

print("Zeilen im liquiden Set:", len(universum_liquide))
print()

alle_ergebnisse = []

# --- Hypothese 1: Gap-Reversal ---
print("=== HYPOTHESE 1: GAP-REVERSAL ===")
print()

universum_liquide = add_gap_signal(universum_liquide, schwelle=0.03)

ergebnis_gap_hoch = run_hypothesis_test(universum_liquide, "gap_hoch", "Gap nach oben (>3%)")
ergebnis_gap_tief = run_hypothesis_test(universum_liquide, "gap_tief", "Gap nach unten (<-3%)")
print(pd.concat([ergebnis_gap_hoch, ergebnis_gap_tief]).to_string(index=False))
alle_ergebnisse += [ergebnis_gap_hoch, ergebnis_gap_tief]

# --- Kontrollgruppe ---
print()
print("=== KONTROLLGRUPPE: HOHE VOLA, KEIN GAP ===")
print()

universum_liquide = add_volatility_control_signal(universum_liquide)
ergebnis_kontrolle = run_hypothesis_test(
    universum_liquide, "hohe_vola_kein_gap", "Kontrolle: hohe Vola, kein Gap"
)
print(ergebnis_kontrolle.to_string(index=False))
alle_ergebnisse.append(ergebnis_kontrolle)

# --- Hypothese 2: 12-1-Momentum ---
print()
print("=== HYPOTHESE 2: 12-1-MOMENTUM ===")
print()

universum_liquide = add_momentum_signal(universum_liquide)
ergebnis_mom_hoch = run_hypothesis_test(universum_liquide, "momentum_hoch", "Momentum hoch (Top 20%)")
ergebnis_mom_tief = run_hypothesis_test(universum_liquide, "momentum_tief", "Momentum tief (Bottom 20%)")
print(pd.concat([ergebnis_mom_hoch, ergebnis_mom_tief]).to_string(index=False))
alle_ergebnisse += [ergebnis_mom_hoch, ergebnis_mom_tief]

# --- Hypothese 3: Volatilitäts-Clustering ---
print()
print("=== HYPOTHESE 3: VOLATILITÄTS-CLUSTERING ===")
print()

universum_liquide = add_forward_volatility_universe(universum_liquide, fenster=(5, 20))
universum_liquide = add_volatility_regime_signal(universum_liquide)

ergebnis_vola_hoch = run_hypothesis_test(
    universum_liquide, "vola_hoch", "Vola hoch (Top 20%)",
    tage_danach=(5, 20), metrik_praefix="fwd_vol_",
)
ergebnis_vola_tief = run_hypothesis_test(
    universum_liquide, "vola_tief", "Vola tief (Bottom 20%)",
    tage_danach=(5, 20), metrik_praefix="fwd_vol_",
)
print(pd.concat([ergebnis_vola_hoch, ergebnis_vola_tief]).to_string(index=False))
alle_ergebnisse += [ergebnis_vola_hoch, ergebnis_vola_tief]

# --- Hypothese 4: Wochentags-Effekte ---
print()
print("=== HYPOTHESE 4: WOCHENTAGS-EFFEKTE ===")
print()

ergebnis_wochentag = test_weekday_effect(universum_liquide)
print(ergebnis_wochentag.to_string(index=False))

# --- Konsolidierte Gesamttabelle ---
print()
print("=== GESAMTÜBERSICHT ALLER HYPOTHESEN ===")
print()

gesamt_tabelle = pd.concat(alle_ergebnisse, ignore_index=True)
print(gesamt_tabelle.to_string(index=False))

ausgabe_pfad = Path("data") / "phase3_hypothesis_results.csv"
gesamt_tabelle.to_csv(ausgabe_pfad, index=False)
print()
print(f"Gespeichert: {ausgabe_pfad}")
print()
print("Phase 3 (Zwischenstand) abgeschlossen. Ergebnis siehe README_Phase3_Ergebnisse.md")