#!/usr/bin/env python3
"""
afriknow_full_817_analysis.py
================================
Analysis script for the full 817-item AfriKnow dataset.

Loads 03_openrouter_outputs_full.csv (multi-row: greedy + vce per model-item),
pivots to wide format, computes metrics, and writes output CSVs compatible with
the v18 analysis format.

Signals computed:
  - VCE (primary)
  - MSP: NOT AVAILABLE (no self-consistency sampling in full run)
  - CoCoA: NOT AVAILABLE (requires MSP)

Outputs:
  scripts/full_817_outputs/
    full_817_accuracy_by_model.csv
    full_817_accuracy_pooled.csv
    full_817_h3_by_model.csv
    full_817_h3_pooled.csv
    full_817_ece_brier_auroc.csv
    full_817_chr.csv
    full_817_flagged_items.csv
    full_817_manifest.md
"""

from __future__ import annotations

import json
import math
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    from sklearn.metrics import roc_auc_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "scripts" / "full_817_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FULL_CSV = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_outputs_full.csv"
MANIFEST_JSON = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_manifest_full.json"
GM_ONLY_JSON = ROOT / "phase2_data" / "afriknow_gm_only_v3.json"

FLAGGED_IDS = [
    "GM-AF-high_school_us_history-test-105",
    "GM-AF-high_school_us_history-test-117",
    "GM-AF-high_school_us_history-test-138",
    "GM-AF-high_school_us_history-test-146",
    "GM-AF-high_school_us_history-test-155",
    "GM-AF-high_school_us_history-test-54",
    "GM-AF-high_school_world_history-test-228",
    "GM-AF-high_school_world_history-test-23",
    "GM-AF-high_school_world_history-test-53",
    "GM-AF-professional_law-test-648",
    "GM-EU-high_school_us_history-test-166",
    "GM-EU-high_school_us_history-test-185",
    "GM-EU-high_school_us_history-test-186",
    "GM-EU-high_school_us_history-test-32",
    "GM-EU-high_school_us_history-test-70",
    "GM-EU-high_school_us_history-test-86",
    "GM-EU-high_school_world_history-test-158",
    "GM-EU-high_school_world_history-test-217",
    "GM-EU-high_school_world_history-test-51",
    "GM-EU-high_school_world_history-test-94",
    "GM-EU-miscellaneous-test-59",
]


def load_full_csv() -> pd.DataFrame:
    df = pd.read_csv(FULL_CSV)
    df["vce"] = pd.to_numeric(df["vce"], errors="coerce")
    df["correct"] = pd.to_numeric(df["correct"], errors="coerce").fillna(0).astype(int)
    return df


def pivot_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    greedy = df[df.purpose == "greedy"][
        ["item_idx", "id", "region", "model", "correct_letter", "cat", "diff", "source", "pred", "correct"]
    ].rename(columns={"pred": "greedy_pred", "correct": "greedy_correct"})

    vce = df[df.purpose == "vce"][
        ["item_idx", "id", "region", "model", "vce", "cocoa_fixed", "greedy_text"]
    ].rename(columns={"vce": "vce", "cocoa_fixed": "cocoa_vce", "greedy_text": "vce_text"})

    wide = greedy.merge(vce, on=["item_idx", "id", "region", "model"], how="left")
    wide["vce"] = wide["vce"].fillna(0.5)
    wide["cocoa_vce"] = wide["cocoa_vce"].fillna(wide["vce"])
    return wide


def compute_ece(conf: np.ndarray, corr: np.ndarray, n_bins: int = 10) -> float:
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (c > lo) & (c <= hi)
        if mask.sum() == 0:
            continue
        acc_b = r[mask].mean()
        conf_b = c[mask].mean()
        ece += (mask.sum() / len(c)) * abs(acc_b - conf_b)
    return float(ece)


def compute_brier(conf: np.ndarray, corr: np.ndarray) -> float:
    return float(np.mean((conf - corr) ** 2))


def compute_auroc(conf: np.ndarray, corr: np.ndarray) -> float:
    if len(np.unique(corr)) < 2:
        return np.nan
    if HAS_SKLEARN:
        return float(roc_auc_score(corr, conf))
    # Manual AUROC using Mann-Whitney U
    pos = conf[corr == 1]
    neg = conf[corr == 0]
    _, p = stats.mannwhitneyu(pos, neg, alternative="greater")
    return float(1.0 - p)


def welch_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    pooled_std = math.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / dof)
    if pooled_std == 0:
        return 0.0
    return float((x.mean() - y.mean()) / pooled_std)


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    pooled_std = math.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    if pooled_std == 0:
        return 0.0
    return float((x.mean() - y.mean()) / pooled_std)


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    n1, n2 = len(x), len(y)
    count = 0
    for xi in x:
        for yi in y:
            if xi > yi:
                count += 1
            elif xi < yi:
                count -= 1
    return float(count / (n1 * n2))


def main():
    log = lambda msg: print(f"[full-817-analysis] {msg}", flush=True)

    log("Loading full 817-item outputs...")
    df = load_full_csv()
    log(f"Loaded {len(df)} rows")

    log("Pivoting to wide format...")
    wide = pivot_to_wide(df)
    log(f"Wide format: {len(wide)} rows ({wide.id.nunique()} items x {wide.model.nunique()} models)")

    # Source control check
    source_counts = wide[["id", "region", "source"]].drop_duplicates()["source"].value_counts()
    log(f"Source distribution: {dict(source_counts)}")

    # GM-only subset
    gm_wide = wide[wide.source == "Global-MMLU (ACL 2025)"].copy()
    log(f"GM-only subset: {gm_wide.id.nunique()} items ({len(gm_wide[gm_wide.region=='Africa'].id.unique())} Africa, {len(gm_wide[gm_wide.region=='Europe'].id.unique())} Europe)")

    models = sorted(wide.model.unique())
    regions = ["Africa", "Europe"]

    # Run analysis on GM-only subset
    analysis_wide = gm_wide
    suffix = "_gm_only"
    acc_rows = []
    for model in models:
        for region in regions:
            sub = analysis_wide[(analysis_wide.model == model) & (analysis_wide.region == region)]
            acc = float(sub.greedy_correct.mean()) if len(sub) > 0 else np.nan
            acc_rows.append({
                "model": model,
                "region": region,
                "n": len(sub),
                "acc": acc,
                "correct": int(sub.greedy_correct.sum()),
            })
    acc_df = pd.DataFrame(acc_rows)
    acc_df.to_csv(OUT_DIR / f"full_817_accuracy_by_model{suffix}.csv", index=False)

    # Pooled accuracy
    pooled_rows = []
    for region in regions:
        sub = analysis_wide[analysis_wide.region == region]
        pooled_rows.append({
            "region": region,
            "n": len(sub),
            "acc": float(sub.greedy_correct.mean()),
            "correct": int(sub.greedy_correct.sum()),
        })
    pooled_df = pd.DataFrame(pooled_rows)
    pooled_df.to_csv(OUT_DIR / f"full_817_accuracy_pooled{suffix}.csv", index=False)

    # H3 by model (VCE only, no MSP/CoCoA)
    h3_rows = []
    for model in models:
        af = analysis_wide[(analysis_wide.model == model) & (analysis_wide.region == "Africa") & (analysis_wide.greedy_correct == 0)]
        eu = analysis_wide[(analysis_wide.model == model) & (analysis_wide.region == "Europe") & (analysis_wide.greedy_correct == 0)]
        if len(af) == 0 or len(eu) == 0:
            continue
        af_vce = af.vce.values
        eu_vce = eu.vce.values
        d = cohens_d(eu_vce, af_vce)
        cd = cliffs_delta(eu_vce, af_vce)
        _, p = stats.mannwhitneyu(eu_vce, af_vce, alternative="two-sided")
        h3_rows.append({
            "model": model,
            "signal": "VCE",
            "n_af": len(af),
            "n_eu": len(eu),
            "af_mean": float(af_vce.mean()),
            "eu_mean": float(eu_vce.mean()),
            "cohens_d": d,
            "cliffs_delta": cd,
            "mannwhitney_p": float(p),
            "status": "supported" if (d > 0 and p < 0.05) else "not supported",
        })
    h3_model_df = pd.DataFrame(h3_rows)
    h3_model_df.to_csv(OUT_DIR / f"full_817_h3_by_model{suffix}.csv", index=False)

    # Pooled H3
    af_all = analysis_wide[(analysis_wide.region == "Africa") & (analysis_wide.greedy_correct == 0)]
    eu_all = analysis_wide[(analysis_wide.region == "Europe") & (analysis_wide.greedy_correct == 0)]
    af_vce = af_all.vce.values
    eu_vce = eu_all.vce.values
    pooled_d = cohens_d(eu_vce, af_vce)
    pooled_cd = cliffs_delta(eu_vce, af_vce)
    _, pooled_p = stats.mannwhitneyu(eu_vce, af_vce, alternative="two-sided")
    pooled_h3 = pd.DataFrame([{
        "signal": "VCE",
        "n_af": len(af_all),
        "n_eu": len(eu_all),
        "af_mean": float(af_vce.mean()),
        "eu_mean": float(eu_vce.mean()),
        "cohens_d": pooled_d,
        "cliffs_delta": pooled_cd,
        "mannwhitney_p": float(pooled_p),
        "status": "supported" if (pooled_d > 0 and pooled_p < 0.05) else "not supported",
    }])
    pooled_h3.to_csv(OUT_DIR / f"full_817_h3_pooled{suffix}.csv", index=False)

    # ECE, Brier, AUROC
    ece_rows = []
    for model in models:
        sub = analysis_wide[analysis_wide.model == model]
        if len(sub) == 0:
            continue
        conf = sub.vce.values
        corr = sub.greedy_correct.values
        ece_rows.append({
            "model": model,
            "signal": "VCE",
            "n": len(sub),
            "ece": compute_ece(conf, corr),
            "brier": compute_brier(conf, corr),
            "auroc": compute_auroc(conf, corr),
        })
    ece_df = pd.DataFrame(ece_rows)
    ece_df.to_csv(OUT_DIR / f"full_817_ece_brier_auroc{suffix}.csv", index=False)

    # CHR (calibration hit rate at high confidence)
    chr_rows = []
    for model in models:
        for region in regions:
            sub = analysis_wide[(analysis_wide.model == model) & (analysis_wide.region == region)]
            high = sub[sub.vce >= 0.80]
            if len(high) == 0:
                continue
            chr_rows.append({
                "model": model,
                "region": region,
                "n_high": len(high),
                "correct": int(high.greedy_correct.sum()),
                "chr": float(high.greedy_correct.mean()),
            })
    chr_df = pd.DataFrame(chr_rows)
    chr_df.to_csv(OUT_DIR / f"full_817_chr{suffix}.csv", index=False)

    # Flagged items
    flagged = analysis_wide[analysis_wide.id.isin(FLAGGED_IDS)].copy()
    flagged.to_csv(OUT_DIR / f"full_817_flagged_items{suffix}.csv", index=False)

    # Manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": __file__,
        "input": str(FULL_CSV),
        "n_items": int(analysis_wide.id.nunique()),
        "n_models": len(models),
        "models": models,
        "n_rows": len(analysis_wide),
        "signals": ["VCE"],
        "missing_signals": ["MSP", "CoCoA"],
        "source_filter": "Global-MMLU (ACL 2025) only",
        "note": "Full 817-item dataset includes AfriMMLU items for Africa region; analysis restricted to GM-only to preserve source control.",
    }
    with open(OUT_DIR / f"full_817_manifest{suffix}.json", "w") as f:
        json.dump(manifest, f, indent=2)

    log("Analysis complete.")
    log(f"Outputs written to {OUT_DIR}")
    log(f"Pooled H3 (VCE): d={pooled_d:.3f}, p={pooled_p:.4f}, n_af={len(af_all)}, n_eu={len(eu_all)}")
    log(f"Pooled accuracy: Africa={pooled_df[pooled_df.region=='Africa'].acc.values[0]:.3f}, Europe={pooled_df[pooled_df.region=='Europe'].acc.values[0]:.3f}")


if __name__ == "__main__":
    main()
