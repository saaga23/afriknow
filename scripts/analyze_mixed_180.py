#!/usr/bin/env python3
"""
Analyze the full 180-item mixed-source OpenRouter run.

Outputs key source-confound contrast statistics:
  - Accuracy by region (Africa vs Europe)
  - Wrong-answer VCE by region (the core H3-style contrast)
  - Per-model breakdown
  - CoCoA / ECE / Brier where computable
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent.parent / "annotator_pipeline" / "outputs"
CSV = OUT_DIR / "03_openrouter_outputs_mixed_180.csv"


def main():
    if not CSV.exists():
        print(f"ERROR: {CSV} not found. Run the mixed-source lane first.")
        sys.exit(1)

    df = pd.read_csv(CSV)
    print(f"Rows: {len(df)}  Items: {df['id'].nunique()}  Models: {df['model'].nunique()}")
    print(f"Regions: {df['region'].unique().tolist()}")

    vce = df[df["purpose"] == "vce"].copy()
    greedy = df[df["purpose"] == "greedy"].copy()

    print("\n=== Accuracy by region (greedy) ===")
    for region, grp in greedy.groupby("region"):
        print(f"  {region}: acc={grp['correct'].mean():.3f} (n={len(grp)})")

    print("\n=== Wrong-answer VCE by region (core contrast) ===")
    for region in ["Africa", "Europe"]:
        wrong = vce[(vce["region"] == region) & (vce["correct"] == 0)]
        print(f"  {region}: mean VCE={wrong['vce'].mean():.3f} (n_wrong={len(wrong)})")

    af = vce[(vce["region"] == "Africa") & (vce["correct"] == 0)]["vce"]
    eu = vce[(vce["region"] == "Europe") & (vce["correct"] == 0)]["vce"]
    if len(af) > 1 and len(eu) > 1:
        diff = af.mean() - eu.mean()
        pooled = np.sqrt(af.var(ddof=1) / len(af) + eu.var(ddof=1) / len(eu))
        t = diff / pooled
        print(f"\n  Africa - Europe wrong-VCE diff = {diff:+.3f}  (t={t:.2f}, pooled_se={pooled:.3f})")

    print("\n=== Per-model wrong-answer VCE by region ===")
    for model, mgrp in vce.groupby("model"):
        afw = mgrp[(mgrp["region"] == "Africa") & (mgrp["correct"] == 0)]["vce"]
        euw = mgrp[(mgrp["region"] == "Europe") & (mgrp["correct"] == 0)]["vce"]
        a = f"{afw.mean():.3f}(n={len(afw)})" if len(afw) else "n/a"
        e = f"{euw.mean():.3f}(n={len(euw)})" if len(euw) else "n/a"
        print(f"  {model:16s} Africa={a:18s} Europe={e}")

    print("\n=== Region source composition (Africa) ===")
    af_items = df[df["region"] == "Africa"]["source"].value_counts()
    for src, n in af_items.items():
        print(f"  {src}: {n}")


if __name__ == "__main__":
    main()
