#!/usr/bin/env python3
"""
create_kaggle_notebook.py
=========================
Creates a Kaggle-compatible version of the v18 analysis notebook.

The original notebook references local paths that don't exist on Kaggle.
This script creates a new notebook that:
1. Reads from the uploaded Kaggle dataset
2. Computes key metrics
3. Generates figures
4. Demonstrates reproducibility
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "kaggle_upload_notebook" / "afriknow-phase-4b-v18-post-hoc-analysis.ipynb"

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# AfriKnow Phase 4B v18 Post-hoc Analysis\n",
                "\n",
                "**Dataset:** [abrahamsunday123/afriknow-v18-inputs](https://www.kaggle.com/datasets/abrahamsunday123/afriknow-v18-inputs)\n",
                "\n",
                "This notebook reproduces the v18 post-hoc analysis for the AfriKnow COLING 2027 submission.\n",
                "\n",
                "**Contents:**\n",
                "- Load 180-item GM-only dataset (7 models, greedy + VCE)\n",
                "- Compute accuracy, calibration metrics, wrong-answer confidence\n",
                "- Generate figures\n",
                "- Verify reproducibility"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import json\n",
                "from pathlib import Path\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "from scipy import stats\n",
                "\n",
                "# Setup paths for Kaggle environment\n",
                "if os.environ.get('KAGGLE_KERNEL_RUN_TYPE') is not None:\n",
                "    ROOT = Path('/kaggle/input/datasets/abrahamsunday123/afriknow-v18-inputs')\n",
                "else:\n",
                "    ROOT = Path('C:/Users/USER/Downloads/Revamp')\n",
                "\n",
                "WORKING = Path('/kaggle/working') if os.environ.get('KAGGLE_KERNEL_RUN_TYPE') else ROOT\n",
                "OUT_DIR = WORKING / 'v18_outputs'\n",
                "FIG_DIR = WORKING / 'v18_analysis_figures'\n",
                "OUT_DIR.mkdir(exist_ok=True)\n",
                "FIG_DIR.mkdir(exist_ok=True)\n",
                "\n",
                "print(f'ROOT: {ROOT}')\n",
                "print(f'OUT_DIR: {OUT_DIR}')\n",
                "print(f'FIG_DIR: {FIG_DIR}')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Load dataset\n",
                "df = pd.read_csv(ROOT / '03_openrouter_outputs_v18_correct.csv')\n",
                "print(f'Loaded {len(df)} rows')\n",
                "print(f'Items: {df[\"item_idx\"].nunique()}')\n",
                "print(f'Models: {sorted(df[\"model\"].unique())}')\n",
                "print(f'Purposes: {sorted(df[\"purpose\"].unique())}')\n",
                "df.head()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Verify data integrity\n",
                "greedy = df[df['purpose'] == 'greedy']\n",
                "vce = df[df['purpose'] == 'vce']\n",
                "\n",
                "print('=== Data Verification ===')\n",
                "print(f'Greedy rows: {len(greedy)}')\n",
                "print(f'VCE rows: {len(vce)}')\n",
                "print(f'VCE non-null: {vce[\"vce\"].notna().sum()}')\n",
                "\n",
                "# Verify accuracy numbers match manuscript\n",
                "af_greedy = greedy[greedy['region'] == 'Africa']\n",
                "eu_greedy = greedy[greedy['region'] == 'Europe']\n",
                "af_acc = af_greedy['correct'].mean()\n",
                "eu_acc = eu_greedy['correct'].mean()\n",
                "\n",
                "print(f'\\nAfrica accuracy: {af_acc:.3f} ({af_greedy[\"correct\"].sum()}/{len(af_greedy)})')\n",
                "print(f'Europe accuracy: {eu_acc:.3f} ({eu_greedy[\"correct\"].sum()}/{len(eu_greedy)})')\n",
                "print(f'Manuscript claims: Africa 87.5%, Europe 85.6%')\n",
                "print(f'Match: {abs(af_acc - 0.875) < 0.001 and abs(eu_acc - 0.856) < 0.001}')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Compute accuracy by model and region\n",
                "acc_rows = []\n",
                "for model in sorted(df['model'].unique()):\n",
                "    for region in ['Africa', 'Europe']:\n",
                "        sub = greedy[(greedy['model'] == model) & (greedy['region'] == region)]\n",
                "        acc = sub['correct'].mean()\n",
                "        acc_rows.append({\n",
                "            'model': model,\n",
                "            'region': region,\n",
                "            'n': len(sub),\n",
                "            'correct': sub['correct'].sum(),\n",
                "            'acc': acc\n",
                "        })\n",
                "\n",
                "acc_df = pd.DataFrame(acc_rows)\n",
                "acc_df.to_csv(OUT_DIR / 'accuracy_by_model.csv', index=False)\n",
                "acc_df.pivot(index='model', columns='region', values='acc').plot(kind='bar')\n",
                "plt.title('Accuracy by Model and Region')\n",
                "plt.ylabel('Accuracy')\n",
                "plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.3)\n",
                "plt.xticks(rotation=45)\n",
                "plt.tight_layout()\n",
                "plt.savefig(FIG_DIR / 'accuracy_by_model.png', dpi=150)\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# H3: Wrong-answer confidence (VCE)\n",
                "wrong_af = vce[(vce['region'] == 'Africa') & (vce['correct'] == 0)]\n",
                "wrong_eu = vce[(vce['region'] == 'Europe') & (vce['correct'] == 0)]\n",
                "\n",
                "print('=== H3: Wrong-Answer Confidence (VCE) ===')\n",
                "print(f'Africa wrong answers: {len(wrong_af)}')\n",
                "print(f'Europe wrong answers: {len(wrong_eu)}')\n",
                "print(f'Africa mean VCE: {wrong_af[\"vce\"].mean():.3f}')\n",
                "print(f'Europe mean VCE: {wrong_eu[\"vce\"].mean():.3f}')\n",
                "\n",
                "# Mann-Whitney U test\n",
                "_, p_val = stats.mannwhitneyu(wrong_eu['vce'], wrong_af['vce'], alternative='two-sided')\n",
                "print(f'Mann-Whitney two-sided p: {p_val:.4f}')\n",
                "print(f'Manuscript claims: d=-0.31, p=.234')\n",
                "print(f'Match: {p_val > 0.05} (not significant, consistent with manuscript)')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Calibration metrics by model\n",
                "from sklearn.metrics import roc_auc_score\n",
                "\n",
                "def compute_ece(conf, corr, n_bins=10):\n",
                "    c = np.asarray(conf, dtype=float)\n",
                "    r = np.asarray(corr, dtype=float)\n",
                "    edges = np.linspace(0.0, 1.0, n_bins + 1)\n",
                "    edges[0] -= 1e-9\n",
                "    edges[-1] += 1e-9\n",
                "    ece = 0.0\n",
                "    for lo, hi in zip(edges[:-1], edges[1:]):\n",
                "        mask = (c > lo) & (c <= hi)\n",
                "        if mask.sum() == 0:\n",
                "            continue\n",
                "        acc_b = r[mask].mean()\n",
                "        conf_b = c[mask].mean()\n",
                "        ece += (mask.sum() / len(c)) * abs(acc_b - conf_b)\n",
                "    return float(ece)\n",
                "\n",
                "def compute_brier(conf, corr):\n",
                "    return float(np.mean((conf - corr) ** 2))\n",
                "\n",
                "ece_rows = []\n",
                "for model in sorted(df['model'].unique()):\n",
                "    sub = vce[vce['model'] == model]\n",
                "    conf = sub['vce'].values\n",
                "    corr = sub['correct'].values\n",
                "    ece_rows.append({\n",
                "        'model': model,\n",
                "        'n': len(sub),\n",
                "        'ece': compute_ece(conf, corr),\n",
                "        'brier': compute_brier(conf, corr),\n",
                "        'auroc': roc_auc_score(corr, conf)\n",
                "    })\n",
                "\n",
                "ece_df = pd.DataFrame(ece_rows)\n",
                "ece_df.to_csv(OUT_DIR / 'ece_brier_auroc.csv', index=False)\n",
                "ece_df"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Generate summary report\n",
                "report = f'''# AfriKnow v18 Analysis Report\n",
                "\n",
                "**Generated:** {pd.Timestamp.now()}\n",
                "\n",
                "## Dataset\n",
                "- Items: {df['item_idx'].nunique()}\n",
                "- Models: {len(df['model'].unique())}\n",
                "- Rows: {len(df)}\n",
                "\n",
                "## Accuracy\n",
                "- Africa: {af_acc:.3f}\n",
                "- Europe: {eu_acc:.3f}\n",
                "\n",
                "## H3 (Wrong-Answer Confidence)\n",
                "- Africa wrong answers: {len(wrong_af)}\n",
                "- Europe wrong answers: {len(wrong_eu)}\n",
                "- Africa mean VCE: {wrong_af['vce'].mean():.3f}\n",
                "- Europe mean VCE: {wrong_eu['vce'].mean():.3f}\n",
                "- Mann-Whitney p: {p_val:.4f}\n",
                "\n",
                "## Calibration\n",
                "```\n",
                "{ece_df.to_string()}\n",
                "```\n",
                "\n",
                "## Verification\n",
                "- Manuscript claims Africa 87.5%, Europe 85.6%: {abs(af_acc - 0.875) < 0.001 and abs(eu_acc - 0.856) < 0.001}\n",
                "- Manuscript claims H3 not significant: {p_val > 0.05}\n",
                "'''\n",
                "\n",
                "with open(OUT_DIR / 'analysis_report.md', 'w') as f:\n",
                "    f.write(report)\n",
                "\n",
                "print(report)\n",
                "print('\\n=== Analysis Complete ===')\n",
                "print(f'Outputs saved to {OUT_DIR}')"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(notebook, f, indent=1)

print(f"Created Kaggle notebook: {OUTPUT_PATH}")
print(f"Size: {OUTPUT_PATH.stat().st_size} bytes")
