from key import DATA_ROOT
from src.data_loader import (
    find_parquet_files,
    load_ticker_history,
    adjust_for_splits,
    add_daily_returns,
    add_outlier_flag,
    event_study,
    plot_price_with_outliers,
    teste_signifikanz,
)


files = find_parquet_files(DATA_ROOT, asset_class="equity")

print("=== Project Valoris — Phase 1: Single-Stock Baseline ===")
print()
print("Gefundene Dateien:", len(files))
print()

aapl = load_ticker_history(files, "AAPL")
aapl = adjust_for_splits(aapl)
aapl = add_daily_returns(aapl)
aapl = add_outlier_flag(aapl)

print(f"AAPL: {len(aapl)} Handelstage, {aapl['timestamp_open_utc'].min().date()} "
      f"bis {aapl['timestamp_open_utc'].max().date()}")
print(f"Ausreißertage: {aapl['ist_ausreisser'].sum()} "
      f"({aapl['ist_ausreisser'].mean() * 100:.2f}%)")
print()

print("=== EVENT STUDY ===")
print()
ergebnis = event_study(aapl)
for zeitraum, gruppen in ergebnis.items():
    print(f"--- {zeitraum} ---")
    for gruppe, werte in gruppen.items():
        print(f"  {gruppe}: {werte['durchschnitt']:.4%} (n={werte['anzahl']})")
    print()

print("=== SIGNIFIKANZ (Positiv-Ausreißer vs. Baseline) ===")
print()
positive_ausreisser = aapl[aapl["ist_ausreisser"] & (aapl["daily_return"] > 0)].index
for n in [1, 5, 20]:
    baseline_werte = [
        (aapl.loc[idx + n, "close"] / aapl.loc[idx, "close"]) - 1
        for idx in aapl.index if idx + n < len(aapl)
    ]
    test = teste_signifikanz(aapl, positive_ausreisser, n, baseline_werte)
    print(f"  {n} Tage danach: p={test['p_wert']:.4f} (n={test['n_events']})")

print()
print("Phase 1 abgeschlossen. Ergebnis siehe README_Phase1_Ergebnisse.md")

print("APPL Aktie visualisierung")

print()
print("=== VISUALISIERUNG ===")
print()

plot_price_with_outliers(
    aapl,
    ticker_name="AAPL",
    speicherpfad="aapl_ausreisser_chart.png",
)