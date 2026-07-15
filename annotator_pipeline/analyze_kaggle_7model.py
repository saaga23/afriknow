#!/usr/bin/env python3
"""
AfriKnow — 7-Model Analysis (Kaggle outputs)
Generates all numbers needed for paper revision.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo')))

import json
import math
import pandas as pd
from scipy import stats
from collections import defaultdict

OUT_DIR = Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo\annotator_pipeline\outputs')
OUT_CSV = OUT_DIR / 'kaggle_8model_outputs.csv'
COST_CSV = OUT_DIR / 'kaggle_8model_cost_history.csv'

df = pd.read_csv(OUT_CSV)
cost_df = pd.read_csv(COST_CSV)

greedy = df[df['purpose'] == 'greedy'].copy()
vce = df[df['purpose'] == 'vce'].copy()

# ─── Helper: Wilson CI ───────────────────────────────────────────────────────

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple:
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    width = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / denom
    return max(0.0, centre - width), min(1.0, centre + width)

# ─── 1. Run Quality ──────────────────────────────────────────────────────────

print("=" * 70)
print("1. RUN QUALITY")
print("=" * 70)

models = sorted(greedy['model'].unique())
print(f"Models ({len(models)}): {models}")
print(f"Total rows: {len(df)} (greedy {len(greedy)}, vce {len(vce)})")
print(f"Items: {df['item_idx'].nunique()}")

call_counts = greedy.groupby('model').size()
print("\nCalls per model:")
for m in models:
    print(f"  {m}: {call_counts.get(m, 0)}")

total_cost = cost_df['cost_usd'].sum()
print(f"\nTotal cost: ${total_cost:.4f}")

# ─── 2. Accuracy (H1) ────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("2. ACCURACY (H1)")
print("=" * 70)

acc_rows = []
for m in models:
    sub = greedy[greedy['model'] == m]
    af = sub[sub['region'] == 'Africa']
    eu = sub[sub['region'] == 'Europe']
    af_acc = af['correct'].mean()
    eu_acc = eu['correct'].mean()
    af_ci = wilson_ci(af['correct'].sum(), len(af))
    eu_ci = wilson_ci(eu['correct'].sum(), len(eu))
    acc_rows.append({
        'model': m,
        'af_n': len(af), 'af_correct': af['correct'].sum(), 'af_acc': af_acc,
        'af_ci_low': af_ci[0], 'af_ci_high': af_ci[1],
        'eu_n': len(eu), 'eu_correct': eu['correct'].sum(), 'eu_acc': eu_acc,
        'eu_ci_low': eu_ci[0], 'eu_ci_high': eu_ci[1],
    })

acc_df = pd.DataFrame(acc_rows)

# Chi-square test (pooled)
af_correct = greedy[greedy['region'] == 'Africa']['correct'].sum()
af_n = len(greedy[greedy['region'] == 'Africa'])
eu_correct = greedy[greedy['region'] == 'Europe']['correct'].sum()
eu_n = len(greedy[greedy['region'] == 'Europe'])

contingency = [[af_correct, af_n - af_correct], [eu_correct, eu_n - eu_correct]]
chi2, p_chi2, _, _ = stats.chi2_contingency(contingency)

print(f"\nPooled accuracy:")
print(f"  Africa: {af_correct}/{af_n} = {af_correct/af_n:.3f}")
print(f"  Europe: {eu_correct}/{eu_n} = {eu_correct/eu_n:.3f}")
print(f"  Chi-square: {chi2:.3f}, p = {p_chi2:.3f}")

print("\nPer-model accuracy:")
for _, row in acc_df.iterrows():
    print(f"  {row['model']:20s}  Africa {row['af_acc']:.3f} [{row['af_ci_low']:.3f}, {row['af_ci_high']:.3f}]  "
          f"Europe {row['eu_acc']:.3f} [{row['eu_ci_low']:.3f}, {row['eu_ci_high']:.3f}]")

# ─── 3. Wrong-Answer VCE (H3) ────────────────────────────────────────────────

print("\n" + "=" * 70)
print("3. WRONG-ANSWER VCE (H3)")
print("=" * 70)

wrong = vce[vce['correct'] == 0].copy()
print(f"Total wrong answers: {len(wrong)}")

h3_rows = []
for m in models:
    sub = wrong[wrong['model'] == m]
    af = sub[sub['region'] == 'Africa']
    eu = sub[sub['region'] == 'Europe']
    af_mean = af['vce'].mean() if len(af) > 0 else float('nan')
    eu_mean = eu['vce'].mean() if len(eu) > 0 else float('nan')
    af_std = af['vce'].std() if len(af) > 1 else 0.0
    eu_std = eu['vce'].std() if len(eu) > 1 else 0.0
    
    # Cohen's d (pooled)
    if len(af) > 1 and len(eu) > 1:
        pooled_std = math.sqrt(((len(af)-1)*af_std**2 + (len(eu)-1)*eu_std**2) / (len(af)+len(eu)-2))
        if pooled_std > 0:
            d = (af_mean - eu_mean) / pooled_std
        else:
            d = 0.0
    else:
        d = float('nan')
    
    # Mann-Whitney U (two-sided)
    if len(af) > 0 and len(eu) > 0:
        try:
            u_stat, p_mwu = stats.mannwhitneyu(af['vce'], eu['vce'], alternative='two-sided')
        except Exception:
            u_stat, p_mwu = float('nan'), float('nan')
    else:
        u_stat, p_mwu = float('nan'), float('nan')
    
    h3_rows.append({
        'model': m,
        'af_n': len(af), 'eu_n': len(eu),
        'af_mean': af_mean, 'eu_mean': eu_mean,
        'diff': af_mean - eu_mean if not math.isnan(af_mean - eu_mean) else float('nan'),
        'd': d,
        'mwu_p': p_mwu,
    })

h3_df = pd.DataFrame(h3_rows)

# Pooled
pooled_af = wrong[wrong['region'] == 'Africa']
pooled_eu = wrong[wrong['region'] == 'Europe']
pooled_af_mean = pooled_af['vce'].mean()
pooled_eu_mean = pooled_eu['vce'].mean()
pooled_af_std = pooled_af['vce'].std()
pooled_eu_std = pooled_eu['vce'].std()
pooled_n_af = len(pooled_af)
pooled_n_eu = len(pooled_eu)
pooled_d = (pooled_af_mean - pooled_eu_mean) / math.sqrt(
    ((pooled_n_af-1)*pooled_af_std**2 + (pooled_n_eu-1)*pooled_eu_std**2) / (pooled_n_af+pooled_n_eu-2)
)

try:
    pooled_u, pooled_p = stats.mannwhitneyu(pooled_af['vce'], pooled_eu['vce'], alternative='two-sided')
except Exception:
    pooled_u, pooled_p = float('nan'), float('nan')

print(f"\nPooled wrong-answer VCE:")
print(f"  Africa: n={pooled_n_af}, mean={pooled_af_mean:.3f}, std={pooled_af_std:.3f}")
print(f"  Europe: n={pooled_n_eu}, mean={pooled_eu_mean:.3f}, std={pooled_eu_std:.3f}")
print(f"  Diff (Af - Eu): {pooled_af_mean - pooled_eu_mean:.3f}")
print(f"  Cohen's d: {pooled_d:.3f}")
print(f"  Mann-Whitney U p (two-sided): {pooled_p:.3f}")

print("\nPer-model wrong-answer VCE:")
for _, row in h3_df.iterrows():
    print(f"  {row['model']:20s}  Af {row['af_n']:3d} {row['af_mean']:.3f}  "
          f"Eu {row['eu_n']:3d} {row['eu_mean']:.3f}  "
          f"diff {row['diff']:+.3f}  d={row['d']:+.3f}  p={row['mwu_p']:.3f}")

# ─── 4. Calibration Hit Rate (H2) ────────────────────────────────────────────

print("\n" + "=" * 70)
print("4. CALIBRATION HIT RATE (H2)")
print("=" * 70)

TAU = 0.70

chr_rows = []
for m in models:
    sub = vce[vce['model'] == m]
    af = sub[sub['region'] == 'Africa']
    eu = sub[sub['region'] == 'Europe']
    
    af_high = af[af['vce'] >= TAU]
    eu_high = eu[eu['vce'] >= TAU]
    
    af_chr = (af_high['correct'] == 0).sum() / len(af_high) if len(af_high) > 0 else float('nan')
    eu_chr = (eu_high['correct'] == 0).sum() / len(eu_high) if len(eu_high) > 0 else float('nan')
    
    ratio = af_chr / eu_chr if eu_chr > 0 else float('nan')
    
    chr_rows.append({
        'model': m,
        'af_chr': af_chr, 'af_n': len(af_high),
        'eu_chr': eu_chr, 'eu_n': len(eu_high),
        'ratio': ratio,
    })

chr_df = pd.DataFrame(chr_rows)

print(f"\nPooled CHR (tau={TAU}):")
pooled_sub = vce
pooled_af = pooled_sub[pooled_sub['region'] == 'Africa']
pooled_eu = pooled_sub[pooled_sub['region'] == 'Europe']
pooled_af_high = pooled_af[pooled_af['vce'] >= TAU]
pooled_eu_high = pooled_eu[pooled_eu['vce'] >= TAU]
pooled_af_chr = (pooled_af_high['correct'] == 0).sum() / len(pooled_af_high) if len(pooled_af_high) > 0 else 0
pooled_eu_chr = (pooled_eu_high['correct'] == 0).sum() / len(pooled_eu_high) if len(pooled_eu_high) > 0 else 0
print(f"  Africa: {pooled_af_chr:.3f} (n={len(pooled_af_high)})")
print(f"  Europe: {pooled_eu_chr:.3f} (n={len(pooled_eu_high)})")
print(f"  Ratio: {pooled_af_chr/pooled_eu_chr:.3f}")

print("\nPer-model CHR:")
for _, row in chr_df.iterrows():
    print(f"  {row['model']:20s}  Af {row['af_chr']:.3f} (n={row['af_n']:3d})  "
          f"Eu {row['eu_chr']:.3f} (n={row['eu_n']:3d})  ratio={row['ratio']:.3f}")

# ─── 5. ECE & Brier ──────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("5. ECE & BRIER")
print("=" * 70)

N_BINS = 10

def compute_ece_brier(sub_df, n_bins=10):
    preds = sub_df['vce'].values
    targets = sub_df['correct'].values
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (preds > bin_boundaries[i]) & (preds <= bin_boundaries[i+1])
        if i == 0:
            mask = (preds >= bin_boundaries[i]) & (preds <= bin_boundaries[i+1])
        if mask.sum() > 0:
            acc = targets[mask].mean()
            conf = preds[mask].mean()
            ece += mask.sum() * abs(acc - conf)
    ece /= len(preds)
    brier = ((preds - targets) ** 2).mean()
    return ece, brier

# Need numpy for this
import numpy as np

ece_rows = []
for m in models:
    sub = vce[vce['model'] == m]
    af = sub[sub['region'] == 'Africa']
    eu = sub[sub['region'] == 'Europe']
    
    af_ece, af_brier = compute_ece_brier(af)
    eu_ece, eu_brier = compute_ece_brier(eu)
    all_ece, all_brier = compute_ece_brier(sub)
    
    ece_rows.append({
        'model': m,
        'ece_af': af_ece, 'ece_eu': eu_ece, 'ece_all': all_ece,
        'brier': all_brier,
    })

ece_df = pd.DataFrame(ece_rows)

print("\nPer-model ECE & Brier:")
for _, row in ece_df.iterrows():
    print(f"  {row['model']:20s}  ECE Af {row['ece_af']:.3f}  Eu {row['ece_eu']:.3f}  "
          f"All {row['ece_all']:.3f}  Brier {row['brier']:.3f}")

# ─── 6. CoCoA Fixed ──────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("6. COCOA FIXED (0.5*vce + 0.5)")
print("=" * 70)

for m in models:
    sub = vce[vce['model'] == m]
    print(f"  {m:20s}  mean={sub['cocoa_fixed'].mean():.3f}")

# ─── 7. Content-Label Mismatches ─────────────────────────────────────────────

print("\n" + "=" * 70)
print("7. CONTENT-LABEL MISMATCHES")
print("=" * 70)

# Need items file
items_path = OUT_DIR.parent / '02_mixed_source_180_items.json'
if items_path.exists():
    with open(items_path, encoding='utf-8') as f:
        items_data = json.load(f)
    items = items_data['items']
    
    flagged = [it for it in items if it.get('flagged', False) or it.get('content_label_mismatch', False)]
    print(f"Flagged items: {len(flagged)} / {len(items)} = {len(flagged)/len(items):.1%}")
else:
    print("Items file not found; skipping mismatch analysis")

# ─── 8. Summary for Paper ────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("8. SUMMARY NUMBERS FOR PAPER")
print("=" * 70)

print(f"\nModels executed: {len(models)}")
print(f"Items: {df['item_idx'].nunique()}")
print(f"Total rows: {len(df)}")
print(f"Total cost: ${total_cost:.4f}")
print(f"\nPooled accuracy:")
print(f"  Africa: {af_correct}/{af_n} = {af_correct/af_n:.1%}")
print(f"  Europe: {eu_correct}/{eu_n} = {eu_correct/eu_n:.1%}")
print(f"  Chi-square: {chi2:.2f}, p = {p_chi2:.3f}")
print(f"\nPooled wrong-answer VCE:")
print(f"  Africa: {pooled_af_mean:.3f} (n={pooled_n_af})")
print(f"  Europe: {pooled_eu_mean:.3f} (n={pooled_n_eu})")
print(f"  Cohen's d: {pooled_d:.3f}")
print(f"  MWU p: {pooled_p:.3f}")
print(f"\nPooled CHR (tau={TAU}):")
print(f"  Africa: {pooled_af_chr:.1%} (n={len(pooled_af_high)})")
print(f"  Europe: {pooled_eu_chr:.1%} (n={len(pooled_eu_high)})")
print(f"  Ratio: {pooled_af_chr/pooled_eu_chr:.2f}")

print("\nDone.")
