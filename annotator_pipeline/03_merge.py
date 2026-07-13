#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 3c: Merge OpenRouter + Modal lanes

Combines:
  - 03_openrouter_outputs.csv (closed models, provider=openrouter)
  - 03_modal_outputs.csv      (open models,   provider=modal)

into a single:
  - 03_model_outputs.csv

with a `provider` column. Validates that both lanes share IDENTICAL columns
(same prompts/schema) before merging -- the core reviewer-proof guarantee.

Also appends to 05_audit_trail.jsonl.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
AUDIT_LOG = OUT_DIR / "05_audit_trail.jsonl"

OR_CSV = OUT_DIR / "03_openrouter_outputs.csv"
MODAL_CSV = OUT_DIR / "03_modal_outputs.csv"
MERGED_CSV = OUT_DIR / "03_model_outputs.csv"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log_event(phase, action, inputs=None, outputs=None, note=""):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase, "action": action, "orchestrator": "03_merge.py",
        "inputs": [{"path": str(p), "sha256": sha256(p), "size": p.stat().st_size} for p in (inputs or []) if p.exists()],
        "outputs": [{"path": str(p), "sha256": sha256(p), "size": p.stat().st_size} for p in (outputs or []) if p.exists()],
        "note": note,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

def main():
    if not OR_CSV.exists():
        raise FileNotFoundError(f"Missing {OR_CSV} -- run 03_openrouter_runner.py first.")
    if not MODAL_CSV.exists():
        raise FileNotFoundError(f"Missing {MODAL_CSV} -- run 03_modal_runner.py first.")

    or_df = pd.read_csv(OR_CSV)
    modal_df = pd.read_csv(MODAL_CSV)

    # Schema identity check (reviewer-proof: both lanes must match)
    or_cols = set(or_df.columns)
    modal_cols = set(modal_df.columns)
    if or_cols != modal_cols:
        missing = modal_cols - or_cols
        extra = or_cols - modal_cols
        raise RuntimeError(f"SCHEMA MISMATCH between lanes! missing_in_or={missing} extra_in_or={extra}")

    or_df = or_df.copy(); or_df["provider"] = "openrouter"
    modal_df = modal_df.copy(); modal_df["provider"] = "modal"

    merged = pd.concat([or_df, modal_df], ignore_index=True)
    merged.to_csv(MERGED_CSV, index=False)

    # Per-provider summary
    summary = {}
    for prov, sub in merged.groupby("provider"):
        greedy = sub[sub.purpose == "greedy"]
        summary[prov] = {
            "rows": int(len(sub)),
            "models": sorted(greedy["model"].unique().tolist()),
            "items": int(greedy["id"].nunique()),
        }

    log_event("03c", "merge", inputs=[OR_CSV, MODAL_CSV], outputs=[MERGED_CSV],
              note=json.dumps({"schema_match": True, "summary": summary}))

    print(f"[merge] Schema match: OK (identical columns)")
    print(f"[merge] OpenRouter rows: {summary['openrouter']['rows']} | models: {summary['openrouter']['models']}")
    print(f"[merge] Modal rows:      {summary['modal']['rows']} | models: {summary['modal']['models']}")
    print(f"[merge] Merged total:    {len(merged)} rows -> {MERGED_CSV}")
    print(f"[merge] Audit event appended to {AUDIT_LOG}")

if __name__ == "__main__":
    main()
