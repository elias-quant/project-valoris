from pathlib import Path
import pandas as pd

from key import DATA_ROOT
from src.data_loader import (
    find_parquet_files,
    save_clean_universe,
    flag_price_outliers_rolling,
    adjust_for_splits_universe,
    add_daily_returns_universe,
    add_outlier_flag_universe,
    add_forward_returns_universe,
    filter_liquid_universe,
    winsorize_column,
    event_study_universe,
)


files = find_parquet_files(DATA_ROOT, asset_class="equity")

print("=== Project Valoris — Phase 2: Multi-Ticker Universe ===")
print()
print("Gefundene Dateien:", len(files))
print()

# --- Dedupliziertes Universum (gecacht) ---
clean_pfad = Path("data") / "clean_universe.parquet"

if clean_pfad.exists():
    universum = pd.read_parquet(clean_pfad)
    print(f"Aus Cache geladen: {clean_pfad}")
else:
    universum = save_clean_universe(files, clean_pfad)

print("Zeilen gesamt:", len(universum))
print("Einzigartige Ticker:", universum["ticker"].nunique())
print()

# --- Bereinigt + Split-adjustiert + Renditen (gecacht) ---
print("=== VERARBEITETES UNIVERSUM (BEREINIGT + SPLIT-ADJUSTIERT + RENDITEN) ===")
print()

verarbeitet_pfad = Path("data") / "universe_processed.parquet"

if verarbeitet_pfad.exists():
    universum = pd.read_parquet(verarbeitet_pfad)
    print(f"Aus Cache geladen: {verarbeitet_pfad}")
else:
    print("Noch kein Cache vorhanden, verarbeite neu (das dauert ein paar Minuten)...")
    universum = flag_price_outliers_rolling(universum, fenster=61, faktor_schwelle=5.0)
    universum = universum[~universum["ist_preis_ausreisser"]].drop(columns=["ist_preis_ausreisser"])
    universum = adjust_for_splits_universe(universum, toleranz=0.15, mindestpreis=1.0)
    universum = add_daily_returns_universe(universum)
    universum.to_parquet(verarbeitet_pfad, index=False)
    print(f"Gespeichert: {verarbeitet_pfad}")

print("Zeilen gesamt:", len(universum))
erste_zeile_pro_ticker = universum.groupby("ticker").head(1)
print("Anzahl erste Zeilen, die NICHT NaN sind (sollte 0 sein):",
      erste_zeile_pro_ticker["daily_return"].notna().sum())
print()

# --- Ausreißer & Forward Returns ---
print("=== AUSREISSER & FORWARD RETURNS ===")
print()

universum = add_outlier_flag_universe(universum)
universum = add_forward_returns_universe(universum)

print("Ausreißertage gesamt:", universum["ist_ausreisser"].sum(),
      f"({universum['ist_ausreisser'].mean() * 100:.2f}%)")
print()

# --- Liquiditätsfilter ---
print("=== LIQUIDITÄTSFILTER ===")
print()

universum_liquide = filter_liquid_universe(universum)
print()

# --- Winsorizing ---
print("=== WINSORIZING (FORWARD RETURNS) ===")
print()

for spalte in ["fwd_1d", "fwd_5d", "fwd_20d"]:
    universum_liquide = winsorize_column(universum_liquide, spalte)
print()

# --- Event Study ---
print("=== EVENT STUDY (LIQUIDE, WINSORIZED) ===")
print()

ergebnis = event_study_universe(universum_liquide)

for zeitraum, gruppen in ergebnis.items():
    print(f"--- {zeitraum} ---")
    for gruppe, werte in gruppen.items():
        zusatz = f", p={werte['p_wert']:.4f}" if "p_wert" in werte else ""
        print(f"  {gruppe}: {werte['durchschnitt']:.4%} (n={werte['anzahl']:,}){zusatz}")
    print()

print("Phase 2 abgeschlossen. Ergebnis siehe README_Phase2_Ergebnisse.md")