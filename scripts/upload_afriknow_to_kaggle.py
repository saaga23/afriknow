#!/usr/bin/env python3
"""
upload_afriknow_to_kaggle.py
=============================
Uploads the corrected AfriKnow v18 dataset to Kaggle.

Dataset: abrahamsunday123/afriknow-v18-inputs
Files included:
  - 03_openrouter_outputs_v18_correct.csv (180 items × 7 models, greedy + VCE)
  - 03_openrouter_manifest_v18.json
  - README.md

Private: yes (credentials stored in Kaggle secrets)
"""

from __future__ import annotations

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
KAGGLE_DIR = ROOT / "kaggle_upload"
DATASET_SLUG = "abrahamsunday123/afriknow-v18-inputs"


def setup_kaggle_credentials():
    """Load Kaggle credentials from .kaggle/kaggle.json"""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print(f"ERROR: Kaggle credentials not found at {kaggle_json}")
        sys.exit(1)

    with open(kaggle_json) as f:
        creds = json.load(f)

    os.environ["KAGGLE_USERNAME"] = creds["username"]
    os.environ["KAGGLE_KEY"] = creds["key"]
    print(f"Loaded Kaggle credentials for user: {creds['username']}")


def create_dataset_metadata():
    """Create dataset-metadata.json for Kaggle"""
    KAGGLE_DIR.mkdir(exist_ok=True)
    metadata = {
        "title": "AfriKnow v18 Inputs - Source-Aware Calibration Audit",
        "id": DATASET_SLUG,
        "description": (
            "Inputs and outputs for the AfriKnow v18 post-hoc analysis. "
            "Contains 180 Global-MMLU items (90 Africa / 90 Europe) evaluated "
            "on 7 language models via OpenRouter. Includes greedy predictions, "
            "verbalized confidence (VCE), self-consistency (MSP), and composite "
            "signals (CoCoA). All raw outputs, cost logs, and manifests are included."
        ),
        "keywords": [
            "nlp",
            "calibration",
            "llm",
            "africa",
            "europe",
            "geographic-bias",
            "multilingual",
            "mmlu",
            "openrouter",
            "afriknow",
        ],
        "collaborators": [],
        "private": True,
    }

    metadata_path = KAGGLE_DIR / "dataset-metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Created dataset metadata: {metadata_path}")
    return metadata_path


def create_readme():
    """Create README.md for the dataset"""
    readme_content = """# AfriKnow v18 Inputs

## Dataset for COLING 2027 Submission

This dataset contains the inputs and outputs for the AfriKnow source-aware calibration audit.

### Contents

- `03_openrouter_outputs_v18_correct.csv` - 180 items × 7 models, greedy + VCE rows
- `03_openrouter_manifest_v18.json` - Run manifest with model list and metadata
- `v18_analysis_outputs/` - Post-hoc analysis CSVs and figures (if included)

### Dataset Details

- **Items:** 180 Global-MMLU items (90 Africa / 90 Europe)
- **Models:** 7 (claude-sonnet-4.6, deepseek-v3.2, gemini-2.5-flash-lite, gemma-4-31b, gpt-4o-mini, gpt-4.1-nano, llama-3.3-70b)
- **Signals:** VCE (primary), MSP, CoCoA (composite)
- **Provider:** OpenRouter API
- **Cost:** ~$1.34
- **Seed:** 42

### Paper

Preprint: [AfriKnow: A Source-Aware Calibration Audit of Seven Language Models](https://arxiv.org/abs/XXXX.XXXXX)

### Citation

```bibtex
@article{abraham2026afriknow,
  title={AfriKnow: A Source-Aware Calibration Audit of Seven Language Models},
  author={Abraham, Sunday Aspita},
  journal={arXiv preprint arXiv:XXXX.XXXXX},
  year={2026}
}
```

### License

CC BY 4.0
"""

    readme_path = KAGGLE_DIR / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)
    print(f"Created README: {readme_path}")
    return readme_path


def copy_files():
    """Copy required files to Kaggle upload directory"""
    KAGGLE_DIR.mkdir(exist_ok=True)

    files_to_copy = {
        ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_outputs_v18_correct.csv": KAGGLE_DIR / "03_openrouter_outputs_v18_correct.csv",
        ROOT / "annotator_pipeline" / "outputs" / "03_openrouter_manifest_v18.json": KAGGLE_DIR / "03_openrouter_manifest_v18.json",
    }

    for src, dst in files_to_copy.items():
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Copied: {src.name} -> {dst}")
        else:
            print(f"WARNING: Source file not found: {src}")


def upload_dataset():
    """Upload dataset to Kaggle"""
    api = KaggleApi()
    api.authenticate()

    print(f"\nUploading dataset to Kaggle: {DATASET_SLUG}")
    print("This may take a few minutes...")

    try:
        api.dataset_create_new(
            folder=str(KAGGLE_DIR),
            dir_mode="zip",
            convert_to_csv=False,
            public=False,  # Private dataset
        )
        print(f"\nDataset uploaded successfully!")
        print(f"URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
    except Exception as e:
        print(f"ERROR uploading dataset: {e}")
        print("\nTroubleshooting:")
        print("1. Verify Kaggle credentials in ~/.kaggle/kaggle.json")
        print("2. Check internet connection")
        print("3. Ensure kaggle package is installed: pip install kaggle")
        sys.exit(1)


def main():
    print("=== AfriKnow Kaggle Upload ===")

    # Setup
    setup_kaggle_credentials()
    create_dataset_metadata()
    create_readme()
    copy_files()

    # List files to upload
    print(f"\nFiles to upload:")
    for f in sorted(KAGGLE_DIR.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}: {size_mb:.2f} MB")

    # Confirm upload
    # response = input("\nProceed with Kaggle upload? [y/N]: ").strip().lower()
    # if response != "y":
    #     print("Upload cancelled.")
    #     return

    upload_dataset()

    print("\n=== Upload complete ===")
    print(f"Dataset URL: https://www.kaggle.com/datasets/{DATASET_SLUG}")
    print("Make sure to update the manuscript with the correct Kaggle links.")


if __name__ == "__main__":
    main()
