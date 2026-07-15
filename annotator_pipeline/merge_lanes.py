#!/usr/bin/env python3
"""
Unified merge and validation for OpenRouter + Modal lanes.

Usage:
    python annotator_pipeline/merge_lanes.py \
        --or outputs/03_openrouter_outputs.csv \
        --modal outputs/03_modal_outputs.csv \
        --out outputs/pilot_merged.csv
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from schema import validate_df, REQUIRED_COLUMNS


def merge_lanes(or_path: Path, modal_path: Path, out_path: Path) -> None:
    or_df = pd.read_csv(or_path)
    modal_df = pd.read_csv(modal_path)

    or_df = or_df[REQUIRED_COLUMNS]
    modal_df = modal_df[REQUIRED_COLUMNS]

    validate_df(or_df)
    validate_df(modal_df)

    merged = pd.concat([or_df, modal_df], ignore_index=True)

    dups = merged.duplicated(subset=["id", "model", "purpose"], keep=False)
    if dups.sum() > 0:
        raise ValueError(f"Duplicate rows detected: {dups.sum()}")

    merged.to_csv(out_path, index=False)
    print(f"Merged {len(or_df)} OR + {len(modal_df)} Modal = {len(merged)} total rows")
    print(f"Saved to {out_path}")

    manifest = {
        "or_rows": len(or_df),
        "modal_rows": len(modal_df),
        "total_rows": len(merged),
        "or_hash": sha256(or_path),
        "modal_hash": sha256(modal_path),
        "output_hash": sha256(out_path),
    }
    manifest_path = out_path.with_suffix(".manifest.json")
    import json
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {manifest_path}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--or", required=True, type=Path, help="OpenRouter outputs CSV")
    parser.add_argument("--modal", required=True, type=Path, help="Modal outputs CSV")
    parser.add_argument("--out", required=True, type=Path, help="Merged output CSV")
    args = parser.parse_args()
    merge_lanes(getattr(args, "or"), args.modal, args.out)


if __name__ == "__main__":
    main()
