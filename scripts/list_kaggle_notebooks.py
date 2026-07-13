#!/usr/bin/env python3
"""List Kaggle notebooks for the user."""

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

try:
    kernels = api.kernels_list(user=creds["username"])
    print(f"Found {len(kernels)} notebooks for {creds['username']}:")
    for k in kernels:
        print(f"  - {k.ref}")
except Exception as e:
    print(f"Error listing notebooks: {e}")
