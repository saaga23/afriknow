#!/usr/bin/env python3
"""
Upload afriknow pilot 50-item dataset to Kaggle.

Dataset: abrahamsunday123/afriknow-pilot-50-gm-only
"""

import json
import os
import shutil
import sys
from pathlib import Path

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    print("ERROR: kaggle package not installed. Install with: pip install kaggle")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = ROOT / "kaggle_upload_pilot"
DATASET_SLUG = "abrahamsunday123/afriknow-pilot-50-gm-only"


def setup_kaggle_credentials():
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print(f"ERROR: Kaggle credentials not found at {kaggle_json}")
        sys.exit(1)

    with open(kaggle_json) as f:
        creds = json.load(f)

    os.environ["KAGGLE_USERNAME"] = creds["username"]
    os.environ["KAGGLE_KEY"] = creds["key"]
    print(f"Loaded Kaggle credentials for user: {creds['username']}")


def upload_dataset():
    api = KaggleApi()
    api.authenticate()

    print(f"\nUploading dataset to Kaggle: {DATASET_SLUG}")
    print("This may take a few minutes...")

    try:
        api.dataset_create_new(
            folder=str(KAGGLE_DIR),
            dir_mode="zip",
            convert_to_csv=False,
            public=False,
        )
        print(f"\nDataset uploaded successfully!")
        print(f"URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
    except Exception as e:
        print(f"ERROR uploading dataset: {e}")
        sys.exit(1)


def main():
    print("=== AfriKnow Pilot 50-Item Dataset Upload ===")

    setup_kaggle_credentials()

    print(f"\nFiles to upload:")
    for f in sorted(KAGGLE_DIR.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name}: {size_kb:.1f} KB")

    upload_dataset()

    print("\n=== Upload complete ===")
    print(f"Dataset URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")


if __name__ == "__main__":
    main()
