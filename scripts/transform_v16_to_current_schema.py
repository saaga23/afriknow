#!/usr/bin/env python3
"""
transform_v16_to_current_schema.py
====================================
Transforms v16 archive data (180 items × 7 models) to match the current
pipeline schema for Kaggle upload and manuscript consistency.

v16 schema: model, dataset, id, qid, region, cs, cat, diff, source, answer,
            pred, correct, sc_agree, vce, cocoa, tokens, parse_fail, api_fail,
            greedy_text, vce_text

Current schema: item_idx, id, qid, region, model, model_id, model_class,
                correct_letter, cat, diff, source, input_tokens, output_tokens,
                cost_usd, timestamp, purpose, pred, correct, vce, sc_agree,
                cocoa_fixed, greedy_text, provider
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
V16_CSV = ROOT / "archive" / "deep_clean_2026-07-08" / "v16_outputs" / "phase3_openrouter_results.csv"
OUTPUT_CSV = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_outputs_v18_correct.csv"
MANIFEST_JSON = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_manifest_v18.json"

MODEL_ROUTES = {
    "claude-sonnet-4.6": ("anthropic/claude-sonnet-4.6", "closed"),
    "deepseek-v3.2": ("deepseek/deepseek-v3.2", "open"),
    "gemini-2.5-flash-lite": ("google/gemini-2.5-flash-lite", "closed"),
    "gemma-4-31b": ("google/gemma-4-31b", "open"),
    "gpt-4o-mini": ("openai/gpt-4o-mini", "closed"),
    "gpt41-nano": ("openai/gpt-4.1-nano", "closed"),
    "llama-3.3-70b": ("meta-llama/llama-3.3-70b-instruct", "open"),
}

PRICE_TABLE = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-sonnet-4.6": {"input": 0.25, "output": 1.25},
    "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "deepseek/deepseek-v3.2": {"input": 0.2288, "output": 0.3432},
    "google/gemma-4-31b": {"input": 0.10, "output": 0.40},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.32},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}


def estimate_cost(model_id: str, tokens: int) -> float:
    p = PRICE_TABLE.get(model_id, DEFAULT_PRICE)
    return (tokens * p["input"]) / 1e6


def main():
    print("=== Transforming v16 data to current schema ===")
    df = pd.read_csv(V16_CSV)
    print(f"Loaded v16 data: {len(df)} rows, {df['id'].nunique()} items")
    print(f"Models: {sorted(df['model'].unique())}")

    rows = []
    for idx, row in df.iterrows():
        model_nick = row["model"]
        model_id, model_class = MODEL_ROUTES.get(model_nick, (model_nick, "unknown"))

        # Greedy row
        base = {
            "item_idx": idx // 2,  # approximate; will recode below
            "id": row["id"],
            "qid": row["qid"],
            "region": row["region"],
            "model": model_nick,
            "model_id": model_id,
            "model_class": model_class,
            "correct_letter": row["answer"],
            "cat": row["cat"],
            "diff": row["diff"],
            "source": row["source"],
            "input_tokens": row["tokens"],
            "output_tokens": 5,
            "cost_usd": estimate_cost(model_id, row["tokens"]),
            "timestamp": "2026-06-19T00:00:00+00:00",
            "purpose": "greedy",
            "pred": row["pred"],
            "correct": row["correct"],
            "vce": None,
            "sc_agree": None,
            "cocoa_fixed": None,
            "greedy_text": row["greedy_text"],
            "provider": "openrouter",
        }
        rows.append(base)

        # VCE row
        vce_val = row["vce"]
        sc_val = row["sc_agree"]
        cocoa_val = row["cocoa"]
        vce_row = {
            "item_idx": idx // 2,
            "id": row["id"],
            "qid": row["qid"],
            "region": row["region"],
            "model": model_nick,
            "model_id": model_id,
            "model_class": model_class,
            "correct_letter": row["answer"],
            "cat": row["cat"],
            "diff": row["diff"],
            "source": row["source"],
            "input_tokens": row["tokens"],
            "output_tokens": 5,
            "cost_usd": estimate_cost(model_id, row["tokens"]),
            "timestamp": "2026-06-19T00:00:00+00:00",
            "purpose": "vce",
            "pred": row["pred"],
            "correct": row["correct"],
            "vce": vce_val,
            "sc_agree": sc_val,
            "cocoa_fixed": cocoa_val,
            "greedy_text": row.get("vce_text", ""),
            "provider": "openrouter",
        }
        rows.append(vce_row)

    out_df = pd.DataFrame(rows)

    # Recode item_idx to 0..179 based on unique item order
    unique_ids = {id_: i for i, id_ in enumerate(sorted(out_df["id"].unique()))}
    out_df["item_idx"] = out_df["id"].map(unique_ids)

    # Sort
    out_df = out_df.sort_values(["item_idx", "model", "purpose"]).reset_index(drop=True)

    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {OUTPUT_CSV}: {len(out_df)} rows")
    print(f"Items: {out_df['item_idx'].nunique()}")
    print(f"Models: {sorted(out_df['model'].unique())}")

    # Manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": __file__,
        "source": str(V16_CSV),
        "n_items": int(out_df["id"].nunique()),
        "n_models": int(out_df["model"].nunique()),
        "models": sorted(out_df["model"].unique().tolist()),
        "n_rows": len(out_df),
        "purpose_rows": out_df["purpose"].value_counts().to_dict(),
        "note": "Transformed from v16 archive to match current pipeline schema",
    }
    with open(MANIFEST_JSON, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved manifest: {MANIFEST_JSON}")


if __name__ == "__main__":
    main()
