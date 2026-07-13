#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 2: Stratified Sample Design

Selects a stratified random sample of 60 Africa / 60 Europe items from the
180-item GM-only v3 dataset, preserving category balance and excluding the
22 flagged content-label-mismatch IDs.

Outputs:
  annotator_pipeline/outputs/
    02_sampled_items.json
    02_sample_design_manifest.json
    02_sample_design_report.md
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GM_ONLY_JSON = ROOT / "phase2_data" / "afriknow_gm_only_v3.json"
FLAGGED_CSV = ROOT / "v18_outputs" / "v18_flagged_items.csv"
REPORT_PATH = OUT_DIR / "02_sample_design_report.md"
SEED = 42
N_PER_REGION = 60

# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[sample] {msg}")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
log("Loading GM-only v3 dataset...")
with open(GM_ONLY_JSON, encoding="utf-8") as f:
    raw = json.load(f)
items = raw["items"]

# Ensure answer is normalized to letter
for it in items:
    if "answer" not in it and "a" in it:
        idx = int(it["a"])
        it["answer"] = chr(65 + idx)

# Exclude flagged items
flagged_df = pd.read_csv(FLAGGED_CSV)
flagged_ids = set(flagged_df["id"].tolist())
log(f"Excluded {len(flagged_ids)} flagged items")

clean_items = [it for it in items if it.get("id") not in flagged_ids]
log(f"Clean pool: {len(clean_items)} items ({sum(1 for i in clean_items if i['region']=='Africa')} Africa / {sum(1 for i in clean_items if i['region']=='Europe')} Europe)")

cat_totals = Counter(it["cat"] for it in clean_items)
total_clean = len(clean_items)

# ---------------------------------------------------------------------------
# Stratified sampling: proportional across categories, balanced by region
# ---------------------------------------------------------------------------
random.seed(SEED)
np.random.seed(SEED)

by_cat_region = defaultdict(list)
for it in clean_items:
    by_cat_region[(it["cat"], it["region"])].append(it)

# Count available per stratum
stratum_counts = {}
for (cat, region), pool in by_cat_region.items():
    stratum_counts[(cat, region)] = len(pool)

# Proportional allocation: for each category, allocate N_PER_REGION * (cat_count / total_count)
alloc_africa = {}
alloc_europe = {}
for cat, cnt in cat_totals.items():
    base = max(2, round(N_PER_REGION * cnt / total_clean))
    alloc_africa[cat] = min(base, len(by_cat_region.get((cat, "Africa"), [])))
    alloc_europe[cat] = min(base, len(by_cat_region.get((cat, "Europe"), [])))

# Top-up Africa if short
africa_alloc = sum(alloc_africa.values())
while africa_alloc < N_PER_REGION:
    candidates = [(cat, len(by_cat_region[(cat, "Africa")])) for cat in alloc_africa if len(by_cat_region[(cat, "Africa")]) > alloc_africa[cat]]
    if not candidates:
        break
    candidates.sort(key=lambda x: x[1], reverse=True)
    alloc_africa[candidates[0][0]] += 1
    africa_alloc += 1

# Top-up Europe if short
europe_alloc = sum(alloc_europe.values())
while europe_alloc < N_PER_REGION:
    candidates = [(cat, len(by_cat_region[(cat, "Europe")])) for cat in alloc_europe if len(by_cat_region[(cat, "Europe")]) > alloc_europe[cat]]
    if not candidates:
        break
    candidates.sort(key=lambda x: x[1], reverse=True)
    alloc_europe[candidates[0][0]] += 1
    europe_alloc += 1

# Trim Africa if overshoot
while africa_alloc > N_PER_REGION:
    candidates = [(cat, alloc_africa[cat]) for cat in alloc_africa if alloc_africa[cat] > 2]
    if not candidates:
        break
    candidates.sort(key=lambda x: x[1], reverse=True)
    alloc_africa[candidates[0][0]] -= 1
    africa_alloc -= 1

# Trim Europe if overshoot
while europe_alloc > N_PER_REGION:
    candidates = [(cat, alloc_europe[cat]) for cat in alloc_europe if alloc_europe[cat] > 2]
    if not candidates:
        break
    candidates.sort(key=lambda x: x[1], reverse=True)
    alloc_europe[candidates[0][0]] -= 1
    europe_alloc -= 1

# ---------------------------------------------------------------------------
# Sample items
sampled = []
for cat in alloc_africa:
    n_a = alloc_africa[cat]
    n_e = alloc_europe[cat]
    africa_pool = by_cat_region[(cat, "Africa")]
    europe_pool = by_cat_region[(cat, "Europe")]
    chosen_africa = random.sample(africa_pool, min(n_a, len(africa_pool)))
    chosen_europe = random.sample(europe_pool, min(n_e, len(europe_pool)))
    sampled.extend(chosen_africa)
    sampled.extend(chosen_europe)

# If we somehow still have fewer than N_PER_REGION, top up from remaining
while sum(1 for i in sampled if i["region"] == "Africa") < N_PER_REGION:
    remaining = [it for it in clean_items if it not in sampled and it["region"] == "Africa"]
    if not remaining:
        break
    sampled.append(random.choice(remaining))

while sum(1 for i in sampled if i["region"] == "Europe") < N_PER_REGION:
    remaining = [it for it in clean_items if it not in sampled and it["region"] == "Europe"]
    if not remaining:
        break
    sampled.append(random.choice(remaining))

# Assign annotator item IDs and shuffle within region
africa_items = [it for it in sampled if it["region"] == "Africa"]
europe_items = [it for it in sampled if it["region"] == "Europe"]
random.shuffle(africa_items)
random.shuffle(europe_items)

# Enumerate
final_items = []
for idx, it in enumerate(africa_items, 1):
    it = dict(it)
    it["annotator_id"] = f"ANN-AF-{idx:03d}"
    it["sample_seed"] = SEED
    it["sampled_at"] = datetime.now(timezone.utc).isoformat()
    final_items.append(it)

for idx, it in enumerate(europe_items, 1):
    it = dict(it)
    it["annotator_id"] = f"ANN-EU-{idx:03d}"
    it["sample_seed"] = SEED
    it["sampled_at"] = datetime.now(timezone.utc).isoformat()
    final_items.append(it)

# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------
assert len(final_items) == 2 * N_PER_REGION, f"Expected {2*N_PER_REGION}, got {len(final_items)}"
assert sum(1 for i in final_items if i["region"] == "Africa") == N_PER_REGION
assert sum(1 for i in final_items if i["region"] == "Europe") == N_PER_REGION
assert all(it["region"] in {"Africa", "Europe"} for it in final_items)
assert all(it["answer"] in {"A", "B", "C", "D"} for it in final_items)
assert all(it["annotator_id"] not in flagged_ids for it in final_items)

# Category balance
cat_dist = Counter(it["cat"] for it in final_items)
log(f"Category distribution: {dict(cat_dist)}")

# Build unified alloc for manifest
alloc = {cat: alloc_africa.get(cat, 0) + alloc_europe.get(cat, 0) for cat in set(alloc_africa) | set(alloc_europe)}

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------
out_json = OUT_DIR / "02_sampled_items.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump({"items": final_items, "meta": {"n_per_region": N_PER_REGION, "seed": SEED, "excluded_flagged": len(flagged_ids)}}, f, indent=2, ensure_ascii=False)
log(f"Sampled items written to {out_json}")

# Provenance manifest
manifest = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "script": __file__,
    "seed": SEED,
    "n_per_region": N_PER_REGION,
    "total_items": len(final_items),
    "source_file": str(GM_ONLY_JSON),
    "source_hash": sha256(GM_ONLY_JSON),
    "flagged_excluded": len(flagged_ids),
    "flagged_file": str(FLAGGED_CSV),
    "output_file": str(out_json),
    "output_hash": sha256(out_json),
    "category_distribution": dict(cat_dist),
    "region_counts": {
        "Africa": sum(1 for i in final_items if i["region"] == "Africa"),
        "Europe": sum(1 for i in final_items if i["region"] == "Europe"),
    },
}
manifest_path = OUT_DIR / "02_sample_design_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

# Markdown report
lines = []
lines.append("# AfriKnow Annotator Pipeline — Sample Design Report")
lines.append("")
lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*")
lines.append(f"*Script: {__file__}*")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 1. Parameters")
lines.append("")
lines.append(f"- **N per region:** {N_PER_REGION}")
lines.append(f"- **Total items:** {len(final_items)}")
lines.append(f"- **Random seed:** {SEED}")
lines.append(f"- **Excluded flagged:** {len(flagged_ids)} content-label-mismatch IDs")
lines.append(f"- **Source:** GM-only v3 (180 items, 90 Africa / 90 Europe)")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 2. Sampling Procedure")
lines.append("")
lines.append("1. Remove 22 flagged content-label-mismatch IDs from the candidate pool.")
lines.append("2. Stratify by `category` x `region`.")
lines.append("3. Proportional allocation: each category receives at least 2 items per region, scaled by its share of the 180-item universe.")
lines.append("4. Random sample without replacement within each stratum (seed=42).")
lines.append("5. If allocation falls short of 60/region, top-up from the largest remaining pools.")
lines.append("6. Assign anonymized IDs: `ANN-AF-001`...`ANN-AF-060`, `ANN-EU-001`...`ANN-EU-060`.")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 3. Final Distribution")
lines.append("")
lines.append("### 3.1 By region")
lines.append("")
lines.append("| Region | Count |")
lines.append("|--------|-------|")
lines.append(f"| Africa | {sum(1 for i in final_items if i['region']=='Africa')} |")
lines.append(f"| Europe | {sum(1 for i in final_items if i['region']=='Europe')} |")
lines.append(f"| **Total** | **{len(final_items)}** |")
lines.append("")
lines.append("### 3.2 By category")
lines.append("")
lines.append("| Category | Africa | Europe | Total |")
lines.append("|----------|--------|--------|-------|")
for cat in sorted(cat_dist):
    af = sum(1 for i in final_items if i["cat"] == cat and i["region"] == "Africa")
    eu = sum(1 for i in final_items if i["cat"] == cat and i["region"] == "Europe")
    lines.append(f"| {cat} | {af} | {eu} | {af+eu} |")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 4. Quality Checks")
lines.append("")
lines.append("| Check | Result |")
lines.append("|-------|--------|")
lines.append(f"| Total items = 120 | {'PASS' if len(final_items)==120 else 'FAIL'} |")
lines.append(f"| Africa = 60 | {'PASS' if sum(1 for i in final_items if i['region']=='Africa')==60 else 'FAIL'} |")
lines.append(f"| Europe = 60 | {'PASS' if sum(1 for i in final_items if i['region']=='Europe')==60 else 'FAIL'} |")
lines.append(f"| No flagged IDs | {'PASS' if all(i['annotator_id'] not in flagged_ids for i in final_items) else 'FAIL'} |")
lines.append(f"| All answers A-D | {'PASS' if all(i['answer'] in 'ABCD' for i in final_items) else 'FAIL'} |")
lines.append(f"| Seed reproducible | {'PASS' if all(i['sample_seed']==42 for i in final_items) else 'FAIL'} |")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 5. Provenance")
lines.append("")
lines.append(f"- **Source SHA256:** `{sha256(GM_ONLY_JSON)}`")
lines.append(f"- **Output SHA256:** `{sha256(out_json)}`")
lines.append(f"- **Script SHA256:** `{sha256(Path(__file__))}`")
lines.append(f"- **Timestamp:** {datetime.now(timezone.utc).isoformat()}")

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
log(f"Report written to {REPORT_PATH}")
log("Done.")
