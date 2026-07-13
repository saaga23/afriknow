#!/usr/bin/env python3
"""Upload afriknow pilot 50-item notebook to Kaggle."""

import json
import os
import shutil
from pathlib import Path

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    print("kaggle package not installed.")
    exit(1)

ROOT = Path(__file__).resolve().parent.parent
KAGGLE_DIR = ROOT / "kaggle_upload_notebook_pilot"


def main():
    # Setup credentials
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    with open(kaggle_json) as f:
        creds = json.load(f)
    os.environ["KAGGLE_USERNAME"] = creds["username"]
    os.environ["KAGGLE_KEY"] = creds["key"]

    print(f"Uploading notebook for user: {creds['username']}")

    # Update kernel metadata with correct username
    kernel_meta_path = KAGGLE_DIR / "kernel-metadata.json"
    with open(kernel_meta_path) as f:
        meta = json.load(f)

    meta["id"] = f"{creds['username']}/afriknow-pilot-50-kaggle"
    meta["dataset_sources"] = [f"{creds['username']}/afriknow-pilot-50-gm-only"]

    with open(kernel_meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    # Upload
    api = KaggleApi()
    api.authenticate()

    print("Uploading notebook to Kaggle...")
    try:
        result = api.kernels_push(folder=str(KAGGLE_DIR))
        print(f"Upload successful!")
        print(f"Notebook URL: https://www.kaggle.com/code/{creds['username']}/afriknow-pilot-50-kaggle")
    except Exception as e:
        print(f"Upload failed: {e}")


if __name__ == "__main__":
    main()
