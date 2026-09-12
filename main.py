import os
from pathlib import Path
import pandas as pd

import key
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
from src.preprocessing import (
    find_file,
    prepare_date_column,
    adjust_prices_for_splits,
    process_dividends,
    merge_dividends_to_prices,
)


def run_phase2():
    files = find_parquet_files(DATA_ROOT, asset_class="equity")

    print("=== Project Valoris — Phase 2: Multi-Ticker Universe ===")
    print()
    print("Gefundene Dateien:", len(files))
    print()

    clean_pfad = Path("data") / "clean_universe.parquet"

    if clean_pfad.exists():
        universum = pd.read_parquet(clean_pfad)
        print(f"Aus Cache geladen: {clean_pfad}")
    else:
        universum = save_clean_universe(files, clean_pfad)

    print("Zeilen gesamt:", len(universum))
    print("Einzigartige Ticker:", universum["ticker"].nunique())
    print()

    print("=== VERARBEITETES UNIVERSUM (BEREINIGT + SPLIT-ADJUSTIERT + RENDITEN) ===")
    print()

    verarbeitet_pfad = Path("data") / "universe_processed.parquet"
    roh_pfad = Path("data") / "universe_raw_deduped.parquet"

    if verarbeitet_pfad.exists():
        universum = pd.read_parquet(verarbeitet_pfad)
        print(f"Aus Cache geladen: {verarbeitet_pfad}")
    else:
        print("Noch kein Cache vorhanden, verarbeite neu (das dauert ein paar Minuten)...")
        universum = flag_price_outliers_rolling(universum, fenster=61, faktor_schwelle=5.0)
        universum = universum[~universum["ist_preis_ausreisser"]].drop(columns=["ist_preis_ausreisser"])

        # Roh-Zwischenstand (bereinigt, aber noch NICHT split-adjustiert) —
        # das ist die Grundlage für die offizielle Corporate-Actions-Adjustierung
        universum.to_parquet(roh_pfad, index=False)
        print(f"Roh-Zwischenstand gespeichert: {roh_pfad}")

        universum = adjust_for_splits_universe(universum, toleranz=0.15, mindestpreis=1.0)
        universum = add_daily_returns_universe(universum)
        universum.to_parquet(verarbeitet_pfad, index=False)
        print(f"Gespeichert: {verarbeitet_pfad}")

    print("Zeilen gesamt:", len(universum))
    erste_zeile_pro_ticker = universum.groupby("ticker").head(1)
    print("Anzahl erste Zeilen, die NICHT NaN sind (sollte 0 sein):",
          erste_zeile_pro_ticker["daily_return"].notna().sum())
    print()

    print("=== AUSREISSER & FORWARD RETURNS ===")
    print()

    universum = add_outlier_flag_universe(universum)
    universum = add_forward_returns_universe(universum)

    print("Ausreißertage gesamt:", universum["ist_ausreisser"].sum(),
          f"({universum['ist_ausreisser'].mean() * 100:.2f}%)")
    print()

    print("=== LIQUIDITÄTSFILTER ===")
    print()

    universum_liquide = filter_liquid_universe(universum)
    print()

    print("=== WINSORIZING (FORWARD RETURNS) ===")
    print()

    for spalte in ["fwd_1d", "fwd_5d", "fwd_20d"]:
        universum_liquide = winsorize_column(universum_liquide, spalte)
    print()

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


def run_corporate_actions_pipeline():
    print("\n--- CORPORATE ACTIONS & DIVIDEND INTEGRATION ---")
    corp_dir = key.DATA_ROOT_CORP_ACTIONS

    div_path = find_file(corp_dir, "dividends.csv")
    splits_path = find_file(corp_dir, "splits.csv")

    print(f"Lade Corporate Actions aus: {corp_dir}...")
    dividends_df = pd.read_csv(div_path)
    splits_df = pd.read_csv(splits_path)

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    roh_pfad = os.path.join(data_dir, "universe_raw_deduped.parquet")

    if not os.path.exists(roh_pfad):
        print("Fehler: universe_raw_deduped.parquet nicht gefunden.")
        print("→ Lösche data/universe_processed.parquet und führe run_phase2() erneut aus.")
        return

    print("Lade Roh-Universum aus Phase 2 (universe_raw_deduped.parquet)...")
    prices_df = pd.read_parquet(roh_pfad)

    print("1. Vorbereitung der Datumsspalte (YYYY-MM-DD)...")
    prices_df = prepare_date_column(prices_df)

    print("2. Führe Split-Bereinigung über Ticker aus...")
    prices_adjusted = adjust_prices_for_splits(prices_df, splits_df)

    print("3. Verarbeite Dividenden und führe Merge aus...")
    div_processed = process_dividends(dividends_df)
    final_df = merge_dividends_to_prices(prices_adjusted, div_processed)

    output_path = os.path.join(data_dir, "universe_with_corporate_actions.parquet")
    final_df.to_parquet(output_path, index=False)
    print(f"\nFertig! Gespeichert unter:\n{output_path}")


if __name__ == "__main__":
    run_phase2()
    run_corporate_actions_pipeline()