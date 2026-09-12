from pathlib import Path
import pandas as pd
from scipy import stats

from src.data_loader import filter_liquid_universe


print("=== Project Valoris — Phase 4b: Total Return & Ex-Dividend-Effekt ===")
print()

df = pd.read_parquet(Path("data") / "universe_with_corporate_actions.parquet")
df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

print("Zeilen geladen:", len(df))
print()

# --- Renditen berechnen: reine Kursrendite vs. Total Return ---
vorheriger_close_adj = df.groupby("ticker")["close_adj"].shift(1)

df["price_return"] = df["close_adj"] / vorheriger_close_adj - 1
df["total_return"] = (df["close_adj"] + df["div_amount_adj"]) / vorheriger_close_adj - 1

# --- Liquiditätsfilter (wie in Phase 2/3) ---
df_liquide = filter_liquid_universe(df)
print()

# --- Vergleich: Kursrendite vs. Total Return über das ganze Universum ---
print("=== KURSRENDITE VS. TOTAL RETURN ===")
print()

mittel_price = df_liquide["price_return"].mean()
mittel_total = df_liquide["total_return"].mean()

print(f"Durchschnittliche tägliche Kursrendite:  {mittel_price:.4%}")
print(f"Durchschnittliche tägliche Total Return: {mittel_total:.4%}")
print(f"Differenz (Dividendenbeitrag/Tag):       {mittel_total - mittel_price:.4%}")
print(f"Hochgerechnet auf ein Jahr (252 Tage):    {(mittel_total - mittel_price) * 252:.2%}")
print()

# --- Ex-Dividend-Drop-Hypothese ---
print("=== EX-DIVIDEND-DROP-EFFEKT ===")
print()

ex_div_tage = df_liquide[df_liquide["div_amount_adj"] > 0]
baseline = df_liquide["price_return"].dropna()

print("Anzahl Ex-Dividenden-Tage (liquide Ticker):", len(ex_div_tage))
print()

signal_werte = ex_div_tage["price_return"].dropna()
_, p_wert = stats.ttest_ind(signal_werte, baseline, equal_var=False)

print(f"Durchschnittliche Kursrendite AM Ex-Div-Tag: {signal_werte.mean():.4%}")
print(f"Baseline (alle Tage):                        {baseline.mean():.4%}")
print(f"Differenz:                                    {signal_werte.mean() - baseline.mean():.4%}")
print(f"p-Wert:                                        {p_wert:.6f}")
print(f"n:                                             {len(signal_werte):,}")
print()

# Durchschnittliche Dividendenrendite an diesen Tagen, zum Vergleich
div_rendite = (ex_div_tage["div_amount_adj"] / vorheriger_close_adj.loc[ex_div_tage.index]).mean()
print(f"Durchschnittliche Dividendenrendite (div/Kurs) an Ex-Div-Tagen: {div_rendite:.4%}")
print("→ Klassische Erwartung: Kursrendite an Ex-Div-Tagen ≈ minus diese Dividendenrendite")