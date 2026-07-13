#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 4: Blinded Annotator Interface Generator

Produces a single CSV where each row is:
  (annotator_id, item_id, question, choices A-D, model_answer, model_confidence, model_family)

Fields:
  - Region labels hidden (Africa/Europe shuffled)
  - Model identities blinded to family labels (Family-A through Family-E)
  - Item IDs anonymized (ANN-AF-001 ... ANN-EU-060)
  - Includes a `gold_answer` column for correctness check (BLINDED in real deployment)

Outputs:
  annotator_pipeline/outputs/
    04_annotator_interface.csv
    04_blinding_key.json          # DO NOT SHARE with annotators
    04_annotator_interface_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
MODEL_OUTPUTS = OUT_DIR / "03_model_outputs.csv"
INTERFACE_CSV = OUT_DIR / "04_annotator_interface.csv"
BLINDING_KEY = OUT_DIR / "04_blinding_key.json"
MANIFEST = OUT_DIR / "04_annotator_interface_manifest.json"

SEED = 42
random.seed(SEED)

FAMILIES = ["openai", "anthropic", "deepseek", "qwen", "meta-llama"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[annotator] {msg}")

# ---------------------------------------------------------------------------
# Load model outputs
log("Loading model outputs...")
df = pd.read_csv(MODEL_OUTPUTS)
# Keep only greedy predictions for annotator interface
greedy = df[df.purpose == "greedy"].copy()
log(f"Loaded {len(greedy)} greedy predictions")

# Build lookup for VCE confidence: (model, id) -> vce
vce_lookup = {}
for _, row in df[df.purpose == "vce"].iterrows():
    vce_lookup[(row["model"], row["id"])] = row.get("vce", None)

# Load sampled items for question text (key by original id for model-output join)
with open(OUT_DIR / "02_sampled_items.json", encoding="utf-8") as f:
    sampled = json.load(f)["items"]
item_map = {it["id"]: it for it in sampled}
annotator_id_map = {it["id"]: it["annotator_id"] for it in sampled}

# ---------------------------------------------------------------------------
# Blinding map
# ---------------------------------------------------------------------------
unique_models = sorted(greedy["model"].unique())

# Explicit, deterministic family assignment (avoids fragile substring matching)
FAMILY_ORDER = ["openai", "anthropic", "deepseek", "qwen", "meta-llama"]
nick_to_family_root = {}
for nick in unique_models:
    assigned = None
    for root in FAMILY_ORDER:
        if nick.lower().startswith(root) or root.replace("-", "") in nick.lower():
            assigned = root
            break
    nick_to_family_root[nick] = assigned or "other"

# Sort unique roots so labels are stable across runs
roots_sorted = sorted(set(nick_to_family_root.values()))
root_to_label = {root: f"Family-{chr(65+i)}" for i, root in enumerate(roots_sorted)}

model_to_family = {}
for nick in unique_models:
    root = nick_to_family_root[nick]
    model_to_family[nick] = root_to_label.get(root, "Family-Other")

# Reverse mapping for the blinding key (DO NOT share with annotators)
family_to_models = defaultdict(list)
for nick, fam in model_to_family.items():
    family_to_models[fam].append(nick)

log(f"Blinding map: {dict(model_to_family)}")

# ---------------------------------------------------------------------------
# Build annotator interface
# ---------------------------------------------------------------------------
rows = []
for _, row in greedy.iterrows():
    orig_id = row.get("id", row.get("qid", ""))
    item = item_map.get(orig_id, {})
    if not item:
        continue
    aid = annotator_id_map.get(orig_id, orig_id)

    fam_label = model_to_family.get(row["model"], "Family-Other")
    rows.append({
        "annotator_item_id": aid,
        "question": item.get("q", ""),
        "choice_a": item.get("ch", ["", "", "", ""])[0] if len(item.get("ch", [])) > 0 else "",
        "choice_b": item.get("ch", ["", "", "", ""])[1] if len(item.get("ch", [])) > 1 else "",
        "choice_c": item.get("ch", ["", "", "", ""])[2] if len(item.get("ch", [])) > 2 else "",
        "choice_d": item.get("ch", ["", "", "", ""])[3] if len(item.get("ch", [])) > 3 else "",
        "model_family": fam_label,
        "model_answer": row["pred"],
        "model_confidence": vce_lookup.get((row["model"], row["id"]), None),
        "gold_answer": item.get("answer", ""),  # BLINDED: remove before giving to annotators
        "_region": item.get("region", ""),      # BLINDED: remove before giving to annotators
        "_model": row["model"],                 # BLINDED: remove before giving to annotators
        "_item_id": aid,                        # BLINDED: remove before giving to annotators
    })

interface_df = pd.DataFrame(rows)

# Create blinded version (remove unblinded columns)
blinded = interface_df[[
    "annotator_item_id", "question", "choice_a", "choice_b", "choice_c", "choice_d",
    "model_family", "model_answer", "model_confidence"
]].copy()

# Shuffle row order
blinded = blinded.sample(frac=1, random_state=SEED).reset_index(drop=True)

# Add annotator columns (to be filled in)
blinded["annotator_correctness"] = ""
blinded["annotator_calibration_ok"] = ""
blinded["annotator_notes"] = ""
blinded["annotator_id_rater"] = ""  # filled by rater
blinded["timestamp"] = ""           # filled by rater

blinded.to_csv(INTERFACE_CSV, index=False)
log(f"Blinded interface saved to {INTERFACE_CSV} ({len(blinded)} rows)")

# ---------------------------------------------------------------------------
# Write blinding key (DO NOT SHARE)
# ---------------------------------------------------------------------------
key = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "seed": SEED,
    "model_to_family": model_to_family,
    "family_to_models": dict(family_to_models),
    "note": "This file links blinded family labels to real model IDs. DO NOT share with annotators.",
    "unblinded_fields": ["gold_answer", "_region", "_model", "_item_id"],
}
BLINDING_KEY.write_text(json.dumps(key, indent=2), encoding="utf-8")
log(f"Blinding key saved to {BLINDING_KEY}")

# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
manifest = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "script": __file__,
    "seed": SEED,
    "input_model_outputs": str(MODEL_OUTPUTS),
    "input_model_outputs_hash": sha256(MODEL_OUTPUTS),
    "output_interface": str(INTERFACE_CSV),
    "output_interface_hash": sha256(INTERFACE_CSV),
    "output_blinding_key": str(BLINDING_KEY),
    "blinding_key_hash": sha256(BLINDING_KEY),
    "n_rows": len(blinded),
    "n_families": len(root_to_label),
    "family_labels": list(root_to_label.values()),
    "model_to_family": model_to_family,
}
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
log(f"Manifest saved to {MANIFEST}")
log("Done.")
