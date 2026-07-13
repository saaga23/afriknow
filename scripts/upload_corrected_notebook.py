#!/usr/bin/env python3
"""Upload corrected notebook to Kaggle."""

import json
import os
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
with open(kaggle_json) as f:
    creds = json.load(f)
os.environ["KAGGLE_USERNAME"] = creds["username"]
os.environ["KAGGLE_KEY"] = creds["key"]

api = KaggleApi()
api.authenticate()

# Push the corrected notebook
result = api.kernels_push(folder=str(Path(__file__).resolve().parent.parent / "kaggle_upload_notebook"))
print(f"Upload successful: {result}")
print(f"Notebook URL: https://www.kaggle.com/code/{creds['username']}/afriknow-phase-4b-v18-post-hoc-analysis")
