# AfriKnow: A Source-Aware Calibration Audit of Seven Language Models

[![COLING 2027](https://img.shields.io/badge/COLING%202027-Submission-blue)](https://coling2027.org)

Official code repository for the AfriKnow paper (COLING 2027 submission). AfriKnow reports a source-aware calibration audit of seven language models on 180 Global-MMLU items balanced across Africa and Europe.

## Key Finding

When benchmark source is held constant (Global-MMLU only), there is **no evidence of higher wrong-answer confidence for Africa** under verbalized confidence (VCE):
- Africa accuracy: 87.5% (551/630)
- Europe accuracy: 85.6% (539/630)
- Wrong-answer VCE: Africa 0.761 vs Europe 0.832 (Cohen's d = -0.31, p = .234)

Apparent regional overconfidence can be absorbed by source confounding.

## Repository Structure

```
afriknow/
├── README.md
├── CITATION.cff
├── LICENSE
├── requirements.txt
├── scripts/
│   ├── afriknow_phase0_metrics.py
│   ├── build_expanded_v3_dataset.py
│   ├── build_pilot_v3.py
│   ├── full_817_analysis.py
│   ├── transform_v16_to_current_schema.py
│   ├── upload_afriknow_to_kaggle.py
│   ├── upload_kaggle_minimal.py
│   ├── make_kaggle_public.py
│   ├── create_kaggle_notebook.py
│   └── test_notebook_local.py
└── data/
    └── README.md
```

## Data

The dataset is available on Kaggle:
- **Dataset:** https://www.kaggle.com/datasets/afriknow-v18-inputs
- **Notebook:** https://www.kaggle.com/code/afriknow-phase-4b-v18-post-hoc-analysis

The dataset contains:
- `03_openrouter_outputs_v18_correct.csv` — 180 items × 7 models, greedy + VCE rows
- `03_openrouter_manifest_v18.json` — Run manifest with model list and metadata

## Setup

```bash
git clone https://github.com/saaga23/afriknow.git
cd afriknow
pip install -r requirements.txt
```

## Dependencies

- Python >= 3.9
- pandas >= 1.5
- numpy >= 1.21
- scipy >= 1.7
- matplotlib >= 3.5
- seaborn >= 0.11
- scikit-learn >= 1.0
- statsmodels >= 0.13

## Reproducing v18 Numbers

```bash
# 1. Download dataset from Kaggle
# Place 03_openrouter_outputs_v18_correct.csv in annotator_pipeline/outputs/

# 2. Verify data integrity
python scripts/test_notebook_local.py

# 3. Run analysis
python scripts/full_817_analysis.py
```

## Citation

```bibtex
@article{abraham2026afriknow,
  title={AfriKnow: A Source-Aware Calibration Audit of Seven Language Models},
  author={Anonymous},
  journal={arXiv preprint arXiv:XXXX.XXXXX},
  year={2026},
  note={COLING 2027 submission}
}
```

## License

MIT License
