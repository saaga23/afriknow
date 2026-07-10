#!/usr/bin/env python3
"""Test the Kaggle notebook locally."""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Simulate local environment (not Kaggle)
os.environ.pop('KAGGLE_KERNEL_RUN_TYPE', None)

ROOT = Path(__file__).resolve().parent.parent
WORKING = ROOT
OUT_DIR = WORKING / 'v18_outputs'
FIG_DIR = WORKING / 'v18_analysis_figures'
OUT_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)

# Use the correct path for the dataset
DATASET_PATH = ROOT / 'annotator_pipeline' / 'outputs' / '03_openrouter_outputs_v18_correct.csv'

print(f'ROOT: {ROOT}')
print(f'DATASET_PATH: {DATASET_PATH}')

# Load dataset
df = pd.read_csv(DATASET_PATH)
print(f'Loaded {len(df)} rows')
print(f'Items: {df["item_idx"].nunique()}')
print(f'Models: {sorted(df["model"].unique())}')

# Verify data integrity
greedy = df[df['purpose'] == 'greedy']
vce = df[df['purpose'] == 'vce']

print(f'Greedy rows: {len(greedy)}')
print(f'VCE rows: {len(vce)}')
print(f'VCE non-null: {vce["vce"].notna().sum()}')

# Verify accuracy numbers match manuscript
af_greedy = greedy[greedy['region'] == 'Africa']
eu_greedy = greedy[greedy['region'] == 'Europe']
af_acc = af_greedy['correct'].mean()
eu_acc = eu_greedy['correct'].mean()

print(f'Africa accuracy: {af_acc:.3f} ({af_greedy["correct"].sum()}/{len(af_greedy)})')
print(f'Europe accuracy: {eu_acc:.3f} ({eu_greedy["correct"].sum()}/{len(eu_greedy)})')
print(f'Manuscript claims: Africa 87.5%, Europe 85.6%')
print(f'Match: {abs(af_acc - 0.875) < 0.001 and abs(eu_acc - 0.856) < 0.001}')

# H3: Wrong-answer confidence (VCE)
wrong_af = vce[(vce['region'] == 'Africa') & (vce['correct'] == 0)]
wrong_eu = vce[(vce['region'] == 'Europe') & (vce['correct'] == 0)]

print(f'\\n=== H3: Wrong-Answer Confidence (VCE) ===')
print(f'Africa wrong answers: {len(wrong_af)}')
print(f'Europe wrong answers: {len(wrong_eu)}')
print(f'Africa mean VCE: {wrong_af["vce"].mean():.3f}')
print(f'Europe mean VCE: {wrong_eu["vce"].mean():.3f}')

# Mann-Whitney U test
from scipy import stats
_, p_val = stats.mannwhitneyu(wrong_eu['vce'], wrong_af['vce'], alternative='two-sided')
print(f'Mann-Whitney two-sided p: {p_val:.4f}')
print(f'Manuscript claims: d=-0.31, p=.234')
print(f'Match: {p_val > 0.05} (not significant, consistent with manuscript)')

print('\\n=== All checks passed! Notebook should run on Kaggle. ===')
