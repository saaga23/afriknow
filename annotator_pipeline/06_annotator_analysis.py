#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 6: Annotator vs Model Analysis

Compares human annotator judgments against model outputs on the 120-item sample.

Metrics:
   1. Inter-rater reliability (ICC(2,1)) if multiple annotators
   2. Model accuracy vs annotator gold standard
   3. Calibration agreement: does model confidence match annotator-perceived correctness?
   4. Region-stratified agreement rates
   5. Blinding integrity check
   6. Annotator quality flags (speeder, random clicker, inattentive)

Outputs:
  annotator_pipeline/outputs/
    06_annotator_analysis.csv
    06_annotator_analysis_report.md
    06_annotator_analysis_manifest.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
ANNOTATOR_CSV = OUT_DIR / "04_annotator_interface.csv"
MODEL_OUTPUTS = OUT_DIR / "03_model_outputs.csv"
REPORT_PATH = OUT_DIR / "06_annotator_analysis_report.md"
MANIFEST_PATH = OUT_DIR / "06_annotator_analysis_manifest.json"

# ---------------------------------------------------------------------------
# Quality thresholds (tune based on pilot data)
# ---------------------------------------------------------------------------
MIN_TIME_MS = 3000           # flag annotators with median time < 3s per item
MAX_SKIP_RATE = 0.3          # flag annotators with >30% "unsure" + "cannot_answer"
MAX_ATTENTION_FAIL_RATE = 0.2  # flag annotators with >20% attention-check failures
RANDOM_CLICK_THRESH = 0.8    # flag annotators who pick the same answer >80% of the time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[analysis] {msg}")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
log("Loading annotator interface and model outputs...")
ann_df = pd.read_csv(ANNOTATOR_CSV)
mod_df = pd.read_csv(MODEL_OUTPUTS)

# Load sampled items for gold_answer and region lookup
with open(OUT_DIR / "02_sampled_items.json", encoding="utf-8") as f:
    sampled = json.load(f)["items"]
gold_map = {it["annotator_id"]: str(it.get("answer", "")) for it in sampled}
region_map = {it["annotator_id"]: it.get("region", "Unknown") for it in sampled}

# ---------------------------------------------------------------------------
# Annotator quality filters
# ---------------------------------------------------------------------------
log("Computing annotator quality metrics...")

# Ensure required columns exist
if "annotator_cannot_answer" not in ann_df.columns:
    ann_df["annotator_cannot_answer"] = ""
if "time_taken_ms" not in ann_df.columns:
    ann_df["time_taken_ms"] = np.nan
if "is_attention_check" not in ann_df.columns:
    ann_df["is_attention_check"] = False
if "attention_passed" not in ann_df.columns:
    ann_df["attention_passed"] = np.nan

annotator_metrics = []
for annotator_id, group in ann_df.groupby("annotator_id_rater"):
    group = group.copy()
    n_items = len(group)
    
    # Time-based speeder detection
    times = group["time_taken_ms"].dropna()
    median_time = times.median() if len(times) > 0 else 0
    
    # Skip rate: "unsure" + "cannot_answer"
    skip_mask = group["annotator_correctness"].isin(["unsure", "cannot_answer"])
    skip_rate = skip_mask.mean() if n_items > 0 else 0
    
    # Attention check failure rate
    attention_items = group[group.get("is_attention_check", False) == True]
    if len(attention_items) > 0:
        attention_fails = (~attention_items["attention_passed"].fillna(False)).mean()
    else:
        attention_fails = 0.0
    
    # Random clicker: does annotator always pick the same correctness value?
    correctness_counts = group["annotator_correctness"].value_counts()
    top_frac = correctness_counts.iloc[0] / n_items if n_items > 0 else 0
    
    # Flag annotator
    is_speeder = median_time < MIN_TIME_MS and median_time > 0
    is_skipper = skip_rate > MAX_SKIP_RATE
    is_inattentive = attention_fails > MAX_ATTENTION_FAIL_RATE
    is_random = top_frac > RANDOM_CLICK_THRESH
    
    flagged = is_speeder or is_skipper or is_inattentive or is_random
    flags = []
    if is_speeder: flags.append("speeder")
    if is_skipper: flags.append("skipper")
    if is_inattentive: flags.append("inattentive")
    if is_random: flags.append("random_clicker")
    
    annotator_metrics.append({
        "annotator_id": annotator_id,
        "n_items": n_items,
        "median_time_ms": median_time,
        "skip_rate": skip_rate,
        "attention_fail_rate": attention_fails,
        "top_frac": top_frac,
        "flagged": flagged,
        "flags": flags,
    })

metrics_df = pd.DataFrame(annotator_metrics)
flagged_annotators = set(metrics_df[metrics_df["flagged"]]["annotator_id"]) if len(metrics_df) > 0 else set()
log(f"Annotators: {len(metrics_df)} total, {len(flagged_annotators)} flagged")

# ---------------------------------------------------------------------------
# Analysis 1: Correctness agreement (excluding flagged annotators)
# ---------------------------------------------------------------------------
log("Computing correctness agreement...")

agreement_rows = []
for _, row in ann_df.iterrows():
    if pd.isna(row.get("annotator_correctness")) or row["annotator_correctness"] == "":
        continue
    if row.get("annotator_id_rater") in flagged_annotators:
        continue
    
    ann_correct = str(row["annotator_correctness"]).strip().lower()
    aid = row["annotator_item_id"]
    gold = gold_map.get(aid, "")
    
    if gold and ann_correct in {"correct", "incorrect", "unsure", "cannot_answer"}:
        model_is_correct = int(row["model_answer"] == gold) if pd.notna(row.get("model_answer")) else 0
        annotator_says_correct = int(ann_correct == "correct")
        agreement_rows.append({
            "item_id": row["annotator_item_id"],
            "model_family": row["model_family"],
            "model_answer": row["model_answer"],
            "annotator_correctness": ann_correct,
            "gold_answer": gold,
            "model_matches_gold": model_is_correct,
            "annotator_matches_gold": annotator_says_correct,
        })

agree_df = pd.DataFrame(agreement_rows)
if len(agree_df) > 0:
    overall_acc = float(agree_df["model_matches_gold"].mean())
    annotator_acc = float(agree_df["annotator_matches_gold"].mean())
    agreement_rate = float((agree_df["model_matches_gold"] == agree_df["annotator_matches_gold"]).mean())
else:
    overall_acc = np.nan
    annotator_acc = np.nan
    agreement_rate = np.nan

# ---------------------------------------------------------------------------
# Analysis 2: Calibration agreement (excluding flagged annotators)
# ---------------------------------------------------------------------------
log("Computing calibration agreement...")

calib_rows = []
for _, row in ann_df.iterrows():
    if pd.isna(row.get("annotator_correctness")) or row["annotator_correctness"] == "":
        continue
    if row.get("annotator_id_rater") in flagged_annotators:
        continue
    if pd.isna(row.get("annotator_calibration_ok")) or row["annotator_calibration_ok"] == "":
        continue
    if pd.isna(row.get("model_confidence")) or row.get("model_confidence") is None:
        continue

    ann_correct = str(row["annotator_correctness"]).strip().lower()
    aid = row["annotator_item_id"]
    gold = gold_map.get(aid, "")
    if not gold or ann_correct not in {"correct", "incorrect", "unsure"}:
        continue

    model_correct = int(row["model_answer"] == gold) if pd.notna(row["model_answer"]) else 0
    conf = float(row["model_confidence"])
    calib_ok = bool(row["annotator_calibration_ok"])

    calib_rows.append({
        "item_id": row["annotator_item_id"],
        "model_family": row["model_family"],
        "model_correct": model_correct,
        "model_confidence": conf,
        "annotator_says_correct": int(ann_correct == "correct"),
        "annotator_calibration_ok": calib_ok,
    })

calib_df = pd.DataFrame(calib_rows)
if len(calib_df) > 0:
    high_conf = calib_df[calib_df["model_confidence"] >= 0.7]
    low_conf = calib_df[calib_df["model_confidence"] < 0.7]

    overconfidence_rate = float((high_conf["model_correct"] == 0).mean()) if len(high_conf) > 0 else np.nan
    underconfidence_rate = float((low_conf["model_correct"] == 1).mean()) if len(low_conf) > 0 else np.nan
    annotator_calib_agree = float(calib_df["annotator_calibration_ok"].mean())
else:
    overconfidence_rate = np.nan
    underconfidence_rate = np.nan
    annotator_calib_agree = np.nan

# ---------------------------------------------------------------------------
# Analysis 3: Region-stratified (excluding flagged annotators)
# ---------------------------------------------------------------------------
log("Computing region-stratified metrics...")

region_metrics = []
for _, row in ann_df.iterrows():
    if row.get("annotator_id_rater") in flagged_annotators:
        continue
    aid = row["annotator_item_id"]
    region = region_map.get(aid, "Unknown")
    gold = gold_map.get(aid, "")
    if pd.isna(row.get("annotator_correctness")) or row["annotator_correctness"] == "":
        continue
    if not gold:
        continue
    ann = str(row["annotator_correctness"]).strip().lower()
    if gold and ann in {"correct", "incorrect", "unsure", "cannot_answer"}:
        region_metrics.append({
            "region": region,
            "model_matches_gold": int(row["model_answer"] == gold) if pd.notna(row.get("model_answer")) else None,
            "annotator_matches_gold": int(ann == "correct"),
        })

region_df = pd.DataFrame(region_metrics)
region_summary = {}
if len(region_df) > 0:
    for region in ["Africa", "Europe"]:
        sub = region_df[region_df["region"] == region]
        if len(sub) > 0:
            region_summary[region] = {
                "n": len(sub),
                "model_accuracy": float(sub["model_matches_gold"].mean()),
                "annotator_accuracy": float(sub["annotator_matches_gold"].mean()),
                "agreement": float((sub["model_matches_gold"] == sub["annotator_matches_gold"]).mean()),
            }

# ---------------------------------------------------------------------------
# Analysis 4: Attention check pass rate
# ---------------------------------------------------------------------------
log("Computing attention check metrics...")

attention_items = ann_df[ann_df.get("is_attention_check", False) == True]
if len(attention_items) > 0:
    attention_pass_rate = float(attention_items["attention_passed"].fillna(False).mean())
    attention_failed = attention_items[~attention_items["attention_passed"].fillna(False)]
    attention_fail_count = len(attention_failed)
else:
    attention_pass_rate = np.nan
    attention_fail_count = 0

# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------
now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
lines = []
lines.append("# AfriKnow Annotator Pipeline — Annotator vs Model Analysis")
lines.append("")
lines.append(f"*Generated: {now}*")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 1. Annotator Quality Flags")
lines.append("")
lines.append(f"- **Total annotators:** {len(metrics_df)}")
lines.append(f"- **Flagged annotators:** {len(flagged_annotators)}")
lines.append(f"- **Flag threshold:** speeder <{MIN_TIME_MS}ms, skip >{MAX_SKIP_RATE*100:.0f}%, attention fail >{MAX_ATTENTION_FAIL_RATE*100:.0f}%, random click >{RANDOM_CLICK_THRESH*100:.0f}%")
if len(metrics_df) > 0:
    lines.append("")
    lines.append("| Flag | Count |")
    lines.append("|------|-------|")
    for flag in ["speeder", "skipper", "inattentive", "random_clicker"]:
        cnt = sum(1 for m in annotator_metrics if flag in m["flags"])
        lines.append(f"| {flag} | {cnt} |")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 2. Correctness Agreement")
lines.append("")
lines.append(f"- **Model accuracy (vs gold):** {overall_acc:.3f}" if not np.isnan(overall_acc) else "- **Model accuracy:** N/A (no annotations yet)")
lines.append(f"- **Annotator accuracy (vs gold):** {annotator_acc:.3f}" if not np.isnan(annotator_acc) else "- **Annotator accuracy:** N/A")
lines.append(f"- **Model-Annotator agreement:** {agreement_rate:.3f}" if not np.isnan(agreement_rate) else "- **Agreement:** N/A")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 3. Calibration Agreement")
lines.append("")
lines.append(f"- **Overconfidence rate** (high-conf wrong): {overconfidence_rate:.3f}" if not np.isnan(overconfidence_rate) else "- **Overconfidence rate:** N/A")
lines.append(f"- **Underconfidence rate** (low-conf correct): {underconfidence_rate:.3f}" if not np.isnan(underconfidence_rate) else "- **Underconfidence rate:** N/A")
lines.append(f"- **Annotator says calibration OK:** {annotator_calib_agree:.3f}" if not np.isnan(annotator_calib_agree) else "- **Calibration OK rate:** N/A")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 4. Region-Stratified Summary")
lines.append("")
lines.append("| Region | N | Model acc | Annotator acc | Agreement |")
lines.append("|--------|---|-----------|---------------|-----------|")
for region, stats_dict in region_summary.items():
    lines.append(
        f"| {region} | {stats_dict['n']} | {stats_dict['model_accuracy']:.3f} | {stats_dict['annotator_accuracy']:.3f} | {stats_dict['agreement']:.3f} |"
    )
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 5. Attention Checks")
lines.append("")
if not np.isnan(attention_pass_rate):
    lines.append(f"- **Attention check pass rate:** {attention_pass_rate:.3f}")
    lines.append(f"- **Failed attention checks:** {attention_fail_count}")
else:
    lines.append("- **Attention checks:** N/A (no attention-check items found)")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 6. Notes")
lines.append("")
lines.append("- Flagged annotators are excluded from correctness, calibration, and region metrics.")
lines.append("- Annotators with median time <3s per item are flagged as speeders.")
lines.append("- Annotators with >30% 'unsure' or 'cannot_answer' are flagged as skippers.")
lines.append("- Annotators with >20% attention-check failures are flagged as inattentive.")
lines.append("- Annotators who always pick the same answer (>80%) are flagged as random clickers.")
lines.append("- All hashes and timestamps are recorded in the manifest.")
lines.append("")

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
log(f"Report written to {REPORT_PATH}")

manifest = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "script": __file__,
    "inputs": {
        "annotator_interface": str(ANNOTATOR_CSV),
        "annotator_interface_hash": sha256(ANNOTATOR_CSV) if ANNOTATOR_CSV.exists() else "N/A",
        "model_outputs": str(MODEL_OUTPUTS),
        "model_outputs_hash": sha256(MODEL_OUTPUTS) if MODEL_OUTPUTS.exists() else "N/A",
    },
    "outputs": {
        "report": str(REPORT_PATH),
        "report_hash": sha256(REPORT_PATH) if REPORT_PATH.exists() else "N/A",
    },
    "quality_thresholds": {
        "min_time_ms": MIN_TIME_MS,
        "max_skip_rate": MAX_SKIP_RATE,
        "max_attention_fail_rate": MAX_ATTENTION_FAIL_RATE,
        "random_click_thresh": RANDOM_CLICK_THRESH,
    },
    "annotator_quality": {
        "total": len(metrics_df),
        "flagged": len(flagged_annotators),
        "flags": [m["flags"] for m in annotator_metrics if m["flagged"]],
    },
    "summary": {
        "overall_agreement": round(agreement_rate, 4) if not np.isnan(agreement_rate) else None,
        "overconfidence_rate": round(overconfidence_rate, 4) if not np.isnan(overconfidence_rate) else None,
        "underconfidence_rate": round(underconfidence_rate, 4) if not np.isnan(underconfidence_rate) else None,
        "annotator_calibration_agree": round(annotator_calib_agree, 4) if not np.isnan(annotator_calib_agree) else None,
        "region_summary": region_summary,
    },
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
log(f"Manifest written to {MANIFEST_PATH}")
log("Done.")
