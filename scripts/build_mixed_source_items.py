#!/usr/bin/env python3
"""
Generate mixed-source contrast items for source-confound demonstration.

Takes 90 Africa items (mix of Global-MMLU + AfriMMLU) and 90 Europe items
(Global-MMLU only), matched by category/difficulty to the GM-only set.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
GM_ONLY_PATH = OUT_DIR / "02_gm_only_180_items.json"
FULL_817_PATH = OUT_DIR / "02_sampled_items_full.json"
MIXED_OUT_PATH = OUT_DIR / "02_mixed_source_180_items.json"

SEED = 42
random.seed(SEED)


def load_json(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    gm_data = load_json(GM_ONLY_PATH)
    full_data = load_json(FULL_817_PATH)

    gm_items = gm_data["items"]
    full_items = full_data["items"]

    # Separate GM-only items by region
    gm_africa = [it for it in gm_items if it["region"] == "Africa"]
    gm_europe = [it for it in gm_items if it["region"] == "Europe"]

    # Get candidate pool from 817 dataset
    full_africa = [it for it in full_items if it["region"] == "Africa"]
    full_europe = [it for it in full_items if it["region"] == "Europe"]

    # Separate Africa candidates by source
    af_gm = [it for it in full_africa if it.get("source") == "Global-MMLU (ACL 2025)"]
    af_afrimmlu = [it for it in full_africa if "AfriMMLU" in it.get("source", "")]

    # Build mixed-source Africa set:
    # For each category in GM-only Africa, try to replace with AfriMMLU equivalents
    # Fall back to Global-MMLU if AfriMMLU unavailable
    target_cats = defaultdict(int)
    for it in gm_africa:
        target_cats[(it["cat"], it["diff"])] += 1

    mixed_africa = []
    afrimmlu_used = set()

    # First pass: use AfriMMLU where available
    for (cat, diff), target_n in sorted(target_cats.items()):
        candidates = [it for it in af_afrimmlu if (it["cat"], it["diff"]) == (cat, diff) and it["id"] not in afrimmlu_used]
        n_pull = min(len(candidates), target_n)
        random.shuffle(candidates)
        mixed_africa.extend(candidates[:n_pull])
        afrimmlu_used.update(it["id"] for it in candidates[:n_pull])
        target_cats[(cat, diff)] -= n_pull

    # Second pass: fill remaining with Global-MMLU Africa
    for (cat, diff), target_n in sorted(target_cats.items()):
        if target_n <= 0:
            continue
        candidates = [it for it in af_gm if (it["cat"], it["diff"]) == (cat, diff) and it["id"] not in afrimmlu_used]
        random.shuffle(candidates)
        mixed_africa.extend(candidates[:target_n])

    # If we still don't have 90, pad with remaining Africa items
    if len(mixed_africa) < 90:
        remaining = [it for it in full_africa if it["id"] not in {x["id"] for x in mixed_africa}]
        random.shuffle(remaining)
        mixed_africa.extend(remaining[: 90 - len(mixed_africa)])

    mixed_africa = mixed_africa[:90]

    # Europe set: Global-MMLU only, matched to GM-only Europe categories
    target_eu_cats = defaultdict(int)
    for it in gm_europe:
        target_eu_cats[(it["cat"], it["diff"])] += 1

    mixed_europe = []
    eu_used = set()

    for (cat, diff), target_n in sorted(target_eu_cats.items()):
        candidates = [it for it in full_europe if (it["cat"], it["diff"]) == (cat, diff) and it["id"] not in eu_used]
        random.shuffle(candidates)
        mixed_europe.extend(candidates[:target_n])
        eu_used.update(it["id"] for it in candidates[:target_n])

    if len(mixed_europe) < 90:
        remaining = [it for it in full_europe if it["id"] not in {x["id"] for x in mixed_europe}]
        random.shuffle(remaining)
        mixed_europe.extend(remaining[: 90 - len(mixed_europe)])

    mixed_europe = mixed_europe[:90]

    # Combine
    mixed_items = mixed_africa + mixed_europe
    random.shuffle(mixed_items)

    # Reassign item_idx
    for idx, it in enumerate(mixed_items):
        it["item_idx"] = idx

    # Compute stats
    af_sources = defaultdict(int)
    for it in mixed_africa:
        af_sources[it.get("source", "unknown")] += 1

    output = {
        "seed": SEED,
        "n_total": len(mixed_items),
        "n_africa": len(mixed_africa),
        "n_europe": len(mixed_europe),
        "gm_only_core": False,
        "description": f"Mixed-source contrast set: 90 Africa (mix of Global-MMLU + AfriMMLU) + 90 Europe (Global-MMLU only). Africa sources: {dict(af_sources)}",
        "items": mixed_items,
    }

    with open(MIXED_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved {MIXED_OUT_PATH}")
    print(f"Total: {len(mixed_items)} (expected 180)")
    print(f"Africa: {len(mixed_africa)} (expected 90)")
    print(f"Europe: {len(mixed_europe)} (expected 90)")
    print(f"Africa sources: {dict(af_sources)}")


if __name__ == "__main__":
    main()
