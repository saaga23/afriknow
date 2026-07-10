#!/usr/bin/env python3
"""
Minimal Kaggle dataset upload using the Kaggle API directly.
"""

import json
import os
import shutil
import sys
from pathlib import Path

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    print("ERROR: kaggle package not installed.")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = ROOT / "kaggle_upload"
DATASET_SLUG = "abrahamsunday123/afriknow-v18-inputs"


def main():
    # Setup credentials
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    with open(kaggle_json) as f:
        creds = json.load(f)
    os.environ["KAGGLE_USERNAME"] = creds["username"]
    os.environ["KAGGLE_KEY"] = creds["key"]

    # Create upload directory
    KAGGLE_DIR.mkdir(exist_ok=True)

    # Minimal metadata
    metadata = {
        "title": "AfriKnow v18 Inputs - Source-Aware Calibration Audit",
        "id": DATASET_SLUG,
        "description": "Inputs for AfriKnow v18 post-hoc analysis. 180 Global-MMLU items (90 Africa / 90 Europe) x 7 models via OpenRouter.",
        "keywords": ["nlp", "calibration", "llm", "africa", "europe", "geographic-bias", "mmlu", "openrouter"],
    }
    with open(KAGGLE_DIR / "dataset-metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Copy data files
    src_csv = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_outputs_v18_correct.csv"
    src_manifest = ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_manifest_v18.json"
    shutil.copy2(src_csv, KAGGLE_DIR / "03_openrouter_outputs_v18_correct.csv")
    shutil.copy2(src_manifest, KAGGLE_DIR / "03_openrouter_manifest_v18.json")

    print("Files prepared:")
    for f in sorted(KAGGLE_DIR.iterdir()):
        print(f"  {f.name}: {f.stat().st_size / 1024:.1f} KB")

    # Upload
    api = KaggleApi()
    api.authenticate()

    print(f"\nUploading to {DATASET_SLUG}...")
    try:
        result = api.dataset_create_new(
            folder=str(KAGGLE_DIR),
            dir_mode="zip",
            convert_to_csv=False,
        )
        print(f"Upload successful!")
        print(f"Dataset URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
    except Exception as e:
        print(f"Upload failed: {e}")
        # Try alternative approach
        print("\nTrying alternative upload method...")
        try:
            result = api.dataset_create_version(
                folder=str(KAGGLE_DIR),
                version_notes="v18 - 180 items x 7 models",
            )
            print(f"Version upload successful!")
        except Exception as e2:
            print(f"Alternative method also failed: {e2}")
            sys.exit(1)


if __name__ == "__main__":
    main()
