import pandas as pd
import key

df = pd.read_parquet("data/universe_with_corporate_actions.parquet")
company_ref = pd.read_csv(rf"{key.DATA_ROOT_CORP_ACTIONS}\company_reference.csv")

unsere_ticker = set(df["ticker"].unique())

cs_referenz = company_ref[company_ref["type"] == "CS"].copy()
cs_referenz["delisted_date"] = pd.to_datetime(cs_referenz["delisted_date"], errors="coerce")

cs_delistet_im_fenster = cs_referenz[
    (~cs_referenz["active"])
    & (cs_referenz["delisted_date"] >= "2016-01-01")
    & (cs_referenz["delisted_date"] <= "2026-12-31")
]

delistet_im_fenster_set = set(cs_delistet_im_fenster["ticker"].unique())
fehlend_im_fenster = delistet_im_fenster_set - unsere_ticker

print("=== SURVIVORSHIP-BIAS-AUDIT ===")
print("Delistete Common Stocks innerhalb 2016-2026:", len(delistet_im_fenster_set))
print("Davon in unseren Preisdaten fehlend:", len(fehlend_im_fenster))
print(f"Anteil: {len(fehlend_im_fenster) / len(delistet_im_fenster_set) * 100:.1f}%")