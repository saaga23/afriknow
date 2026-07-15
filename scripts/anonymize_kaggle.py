#!/usr/bin/env python3
"""
Anonymize Kaggle dataset metadata and files for double-blind submission.

This script:
1. Replaces author Kaggle handle with anonymous handle in dataset-metadata.json
2. Updates dataset title/description to remove PII
3. Creates an anonymized README for the dataset

Usage:
    python scripts/anonymize_kaggle.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = ROOT.parent / "kaggle_upload"
ANON_HANDLE = "afriknow-anon"


def anonymize_metadata(path: Path) -> None:
    with open(path, encoding="utf-8") as f:
        meta = json.load(f)

    meta["title"] = "AfriKnow v18 Inputs (Anonymous)"
    meta["subtitle"] = "Source-Aware Calibration Audit Dataset"
    meta["description"] = re.sub(
        r"abrahamsunday123", ANON_HANDLE, meta.get("description", "")
    )
    meta["id"] = f"{ANON_HANDLE}/afriknow-v18-inputs"
    meta["keywords"] = ["calibration", "llm", "africa", "europe", "mmlu"]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Anonymized {path}")


def anonymize_readme(path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    content = re.sub(r"abrahamsunday123", ANON_HANDLE, content)
    path.write_text(content, encoding="utf-8")
    print(f"Anonymized {path}")


def main():
    anonymize_metadata(KAGGLE_DIR / "dataset-metadata.json")
    anonymize_readme(KAGGLE_DIR / "README.md")
    print("Kaggle anonymization complete.")


if __name__ == "__main__":
    main()
