"""
build_pilot_v3.py
=================
Freeze a small, standard pilot subset from the v3 datasets.

Rationale
---------
A common rule-of-thumb for a useful pilot/feasibility sample is at least
30 observations per group. We therefore sample 30 items per region from the
full v3 set (60 total) and 30 matched pairs from the GM-only v3 set
(60 total). This is the smallest sample that still gives:

  * enough items to exercise the full pipeline (greedy + VCE + 5×SC),
  * a rough per-model effect-size estimate,
  * a meaningful check on parse-failure rates and API behavior,
  * while keeping cost low (~$1.56/model conservative, 7 models ≈ $11 total).

Outputs in ./phase2_data/:
  - afriknow_pilot_full_v3.json
  - afriknow_pilot_gm_only_v3.json

Run:
    python build_pilot_v3.py
"""

import json
import os
import random
from collections import Counter, defaultdict

import pandas as pd

SEED = 42
random.seed(SEED)
os.makedirs("phase2_data", exist_ok=True)

PILOT_N_PER_REGION = 30


def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def stratified_sample(items, n_per_region):
    """Sample n_per_region items per region, stratified by source when possible."""
    groups = defaultdict(list)
    for it in items:
        groups[it["region"]].append(it)

    out = []
    for region in ["Africa", "Europe"]:
        pool = groups.get(region, [])
        if len(pool) < n_per_region:
            raise ValueError(
                f"Not enough {region} items for pilot: {len(pool)} < {n_per_region}"
            )
        # Preserve source proportions within the region by sorting and sampling
        # deterministically with a fixed seed.
        pool_sorted = sorted(pool, key=lambda x: (x.get("source", ""), x.get("id", "")))
        out.extend(random.sample(pool_sorted, n_per_region))

    random.shuffle(out)
    return out


def sample_matched_pairs(items, n_pairs):
    """Sample n_pairs matched Africa/Europe pairs from a GM-only set."""
    africa = [it for it in items if it["region"] == "Africa"]
    europe = [it for it in items if it["region"] == "Europe"]

    # Build pairing keys. Because gm_only was built by matching on
    # (subject, difficulty, cs), we can sample pairs by matching on those keys.
    af_by_key = defaultdict(list)
    eu_by_key = defaultdict(list)
    for it in africa:
        af_by_key[(it["cat"], it["diff"], it["cs"])].append(it)
    for it in europe:
        eu_by_key[(it["cat"], it["diff"], it["cs"])].append(it)

    pairs = []
    for key in af_by_key:
        n_available = min(len(af_by_key[key]), len(eu_by_key.get(key, [])))
        pairs.extend([key] * n_available)

    if len(pairs) < n_pairs:
        raise ValueError(
            f"Not enough matched pairs for pilot: {len(pairs)} < {n_pairs}"
        )

    rng = random.Random(SEED)
    selected_keys = rng.sample(pairs, n_pairs)
    key_counts = Counter(selected_keys)

    out = []
    for key, count in key_counts.items():
        af_sample = rng.sample(af_by_key[key], count)
        eu_sample = rng.sample(eu_by_key[key], count)
        out.extend(af_sample)
        out.extend(eu_sample)

    rng.shuffle(out)
    return out


def build_pilot_dataset(name, items, n_per_region, is_gm_only):
    if is_gm_only:
        pilot_items = sample_matched_pairs(items, n_per_region)
    else:
        pilot_items = stratified_sample(items, n_per_region)

    region_counts = Counter(it["region"] for it in pilot_items)
    source_counts = Counter(it.get("source", "unknown") for it in pilot_items)

    return {
        "name": name,
        "version": "phase2_pilot_v3",
        "description": (
            f"Frozen pilot subset sampled from v3 with {PILOT_N_PER_REGION} "
            "items per region. Intended for pipeline validation and rough "
            "effect-size estimation, not for hypothesis testing."
        ),
        "items": pilot_items,
        "statistics": {
            "n_total": len(pilot_items),
            "n_africa": region_counts["Africa"],
            "n_europe": region_counts["Europe"],
            "source_counts": dict(source_counts),
        }
    }


def audit(dataset):
    items = dataset["items"]
    print(f"\n--- Audit: {dataset['name']} ---")
    print(f"Total items: {len(items)}")
    df = pd.DataFrame(items)
    print("\nRegion x CS:")
    print(pd.crosstab(df["cs"], df["region"]))
    print("\nSource x Region:")
    print(pd.crosstab(df["source"], df["region"]))
    assert df["region"].isin(["Africa", "Europe"]).all()
    print("Validation OK")


def main():
    full_v3 = load_items("phase2_data/afriknow_source_annotated_full_v3.json")
    gm_only_v3 = load_items("phase2_data/afriknow_gm_only_v3.json")

    pilot_full = build_pilot_dataset(
        "AfriKnow pilot full v3", full_v3["items"], PILOT_N_PER_REGION, is_gm_only=False
    )
    pilot_gm = build_pilot_dataset(
        "AfriKnow pilot GM-only v3", gm_only_v3["items"], PILOT_N_PER_REGION, is_gm_only=True
    )

    audit(pilot_full)
    audit(pilot_gm)

    with open("phase2_data/afriknow_pilot_full_v3.json", "w", encoding="utf-8") as f:
        json.dump(pilot_full, f, ensure_ascii=False, indent=2)
    with open("phase2_data/afriknow_pilot_gm_only_v3.json", "w", encoding="utf-8") as f:
        json.dump(pilot_gm, f, ensure_ascii=False, indent=2)

    print("\nSaved pilot artefacts to ./phase2_data/:")
    print("  - afriknow_pilot_full_v3.json")
    print("  - afriknow_pilot_gm_only_v3.json")


if __name__ == "__main__":
    main()
