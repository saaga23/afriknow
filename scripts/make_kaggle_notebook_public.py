#!/usr/bin/env python3
"""Make Kaggle notebook public."""

import json
import os
from pathlib import Path

try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    print("kaggle package not installed.")
    exit(1)

kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
with open(kaggle_json) as f:
    creds = json.load(f)
os.environ["KAGGLE_USERNAME"] = creds["username"]
os.environ["KAGGLE_KEY"] = creds["key"]

api = KaggleApi()
api.authenticate()

# Update kernel metadata to public
KAGGLE_DIR = Path(__file__).resolve().parent.parent / "kaggle_upload_notebook"
kernel_meta_path = KAGGLE_DIR / "kernel-metadata.json"

with open(kernel_meta_path) as f:
    meta = json.load(f)
meta["is_private"] = False
with open(kernel_meta_path, "w") as f:
    json.dump(meta, f, indent=2)

print("Updating notebook to public...")
try:
    result = api.kernels_push(folder=str(KAGGLE_DIR))
    print(f"Success: {result}")
    print(f"Notebook URL: https://www.kaggle.com/code/{creds['username']}/afriknow-phase-4b-v18-post-hoc-analysis")
except Exception as e:
    print(f"Error: {e}")
