#!/usr/bin/env python3
"""Upload v18 analysis notebook to Kaggle."""

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
KAGGLE_DIR = ROOT / "kaggle_upload_notebook"
KAGGLE_DIR.mkdir(exist_ok=True)

# Setup credentials
kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
with open(kaggle_json) as f:
    creds = json.load(f)
os.environ["KAGGLE_USERNAME"] = creds["username"]
os.environ["KAGGLE_KEY"] = creds["key"]

# Copy notebook
src = ROOT / "archive" / "deep_clean_2026-07-08" / "phase4b_v18_analysis.ipynb"
dst = KAGGLE_DIR / "afriknow-phase-4b-v18-post-hoc-analysis.ipynb"
shutil.copy2(src, dst)
print(f"Copied notebook: {dst.name} ({dst.stat().st_size} bytes)")

# Create minimal metadata for kernel
kernel_meta = {
    "id": f"{creds['username']}/afriknow-phase-4b-v18-post-hoc-analysis",
    "title": "AfriKnow Phase 4B v18 Post-hoc Analysis",
    "code_file": "afriknow-phase-4b-v18-post-hoc-analysis.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": False,
    "enable_internet": True,
    "keywords": ["nlp", "calibration", "llm", "africa", "europe"],
    "dataset_sources": [
        f"{creds['username']}/afriknow-v18-inputs"
    ],
}

with open(KAGGLE_DIR / "kernel-metadata.json", "w") as f:
    json.dump(kernel_meta, f, indent=2)
print("Created kernel-metadata.json")

# Upload
api = KaggleApi()
api.authenticate()

print("Uploading notebook to Kaggle...")
try:
    result = api.kernels_push(folder=str(KAGGLE_DIR))
    print(f"Upload successful!")
    print(f"Notebook URL: https://www.kaggle.com/code/{creds['username']}/afriknow-phase-4b-v18-post-hoc-analysis")
except Exception as e:
    print(f"Upload failed: {e}")
