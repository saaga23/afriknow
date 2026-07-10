#!/usr/bin/env python3
"""Make Kaggle dataset public by updating metadata and creating new version."""

import json
import os
from pathlib import Path

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    print("kaggle package not installed.")
    exit(1)

ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = ROOT / "kaggle_upload"
DATASET_SLUG = "abrahamsunday123/afriknow-v18-inputs"

# Setup credentials
kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
with open(kaggle_json) as f:
    creds = json.load(f)
os.environ["KAGGLE_USERNAME"] = creds["username"]
os.environ["KAGGLE_KEY"] = creds["key"]

# Update metadata to public
metadata_path = KAGGLE_DIR / "dataset-metadata.json"
with open(metadata_path) as f:
    meta = json.load(f)
meta["private"] = False
with open(metadata_path, "w") as f:
    json.dump(meta, f, indent=2)
print(f"Updated metadata: private={meta['private']}")

# Upload new version
api = KaggleApi()
api.authenticate()

print("Creating new public version...")
try:
    result = api.dataset_create_version(
        folder=str(KAGGLE_DIR),
        version_notes="v18 - made public for COLING 2027 reviewers",
    )
    print(f"Success: {result}")
    print(f"Dataset URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
except Exception as e:
    print(f"Error: {e}")
