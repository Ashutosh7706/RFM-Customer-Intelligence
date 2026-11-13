"""Rebuild customer-level RFM metrics and project visuals from the bundled sales data.
Run from the repository root: python code/run_analysis.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "sales_asia.csv"
OUT = ROOT / "output"
MEDIA = ROOT / "media"
OUT.mkdir(exist_ok=True); MEDIA.mkdir(exist_ok=True)

tx = pd.read_csv(DATA, sep=";", decimal=",", dtype={"week.year": str})
parts = tx["week.year"].str.split(".", expand=True)
tx["date"] = pd.to_datetime(parts[1] + parts[0] + "-1", format="%Y%W-%w", errors="coerce")
tx = tx.dropna(subset=["date"]).rename(columns={"revenue": "monetary"})
now = tx["date"].max() + pd.Timedelta(days=1)
window = tx.loc[tx["date"] >= now - pd.Timedelta(days=365)].copy()
window["customer_key"] = window["country"].astype(str) + window["id"].astype(str)
rfm = window.groupby(["id", "customer_key", "country"], as_index=False).agg(
    recency=("date", lambda s: (now - s.max()).days),
    frequency=("date", "size"), monetary=("monetary", "sum"))
q = rfm[["recency", "frequency", "monetary"]].quantile([.2, .4, .6, .8])
def r_score(x):
    return 5 if x <= q.loc[.2, "recency"] else 4 if x <= q.loc[.4, "recency"] else 3 if x <= q.loc[.6, "recency"] else 2 if x <= q.loc[.8, "recency"] else 1
def fm_score(x, col):
    return 1 if x <= q.loc[.2, col] else 2 if x <= q.loc[.4, col] else 3 if x <= q.loc[.6, col] else 4 if x <= q.loc[.8, col] else 5
rfm["r"] = rfm["recency"].map(r_score)
rfm["f"] = rfm["frequency"].map(lambda x: fm_score(x, "frequency"))
rfm["m"] = rfm["monetary"].map(lambda x: fm_score(x, "monetary"))
rfm["rfm_score"] = rfm[["r", "f", "m"]].astype(str).agg("".join, axis=1)
rfm["fm"] = ((rfm["f"] + rfm["m"]) / 2).apply(np.trunc).astype(int)
segment_map = [(r"22", "hibernating"), (r"[1-2][1-2]", "lost"), (r"15", "can't lose"), (r"[1-2][3-5]", "at risk"), (r"3[1-2]", "about to sleep"), (r"33", "need attention"), (r"55", "champions"), (r"[3-5][4-5]", "loyal customers"), (r"41", "promising"), (r"51", "new customers"), (r"[4-5][2-3]", "potential loyalists")]
def classify(code):
    for pattern, label in segment_map:
        if re.fullmatch(pattern, code): return label
    return "unclassified"
rfm["segment"] = (rfm["r"].astype(str) + rfm["fm"].astype(str)).map(classify)
rfm.drop(columns="customer_key").to_csv(OUT / "rfm_asia.csv", index=False, float_format="%.2f")
print(f"Saved {len(rfm):,} customer records to {OUT / 'rfm_asia.csv'}")
print(rfm["segment"].value_counts().to_string())
