#!/usr/bin/env python3
"""
Re-run mixed-effects models on 7-model Kaggle outputs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo')))

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

OUT_DIR = Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo\annotator_pipeline\outputs')
df = pd.read_csv(OUT_DIR / 'kaggle_8model_outputs.csv')
vce = df[df['purpose'] == 'vce'].copy()

vce['region_code'] = (vce['region'] == 'Africa').astype(int)
vce['model_code'] = vce['model'].astype('category').cat.codes
vce['correct_int'] = vce['correct'].astype(int)

print("=" * 70)
print("MIXED-EFFECTS MODELS (VCE)")
print("=" * 70)

# ─── 1. Marginal logistic regression for accuracy ────────────────────────────

print("\n1. Accuracy: marginal logistic regression (cluster-robust SEs by qid)")

formula_acc = "correct_int ~ C(region) + C(model)"
acc_model = smf.logit(formula_acc, data=vce).fit(cov_type='cluster', cov_kwds={'groups': vce['qid']})

# Extract key values
acc_params = acc_model.params
acc_bse = acc_model.bse
acc_pvalues = acc_model.pvalues

print(f"Intercept: {acc_params['Intercept']:.4f} (SE {acc_bse['Intercept']:.4f}, p={acc_pvalues['Intercept']:.4f})")
print(f"region[T.Europe]: {acc_params['C(region)[T.Europe]']:.4f} (SE {acc_bse['C(region)[T.Europe]']:.4f}, p={acc_pvalues['C(region)[T.Europe]']:.4f})")
print(f"z = {acc_params['C(region)[T.Europe]']/acc_bse['C(region)[T.Europe]']:.2f}")

# Model fixed effects
for m in ['deepseek-v3.2', 'gemini-2.5-flash-lite', 'gpt-4.1-nano', 'gpt-4o-mini', 'llama-3.3-70b', 'qwen3-235b']:
    col = f"C(model)[T.{m}]"
    if col in acc_params:
        print(f"{m}: coef={acc_params[col]:.4f}, SE={acc_bse[col]:.4f}, p={acc_pvalues[col]:.4f}")

# ─── 2. Logit-normal linear mixed model for confidence ───────────────────────

print("\n2. Confidence: logit-normal linear mixed model")
print("   logit(vce) ~ region + model + (1 | qid)")

vce['vce_clipped'] = vce['vce'].clip(0.001, 0.999)
vce['logit_vce'] = np.log(vce['vce_clipped'] / (1 - vce['vce_clipped']))

try:
    conf_model = smf.mixedlm("logit_vce ~ C(region) + C(model)", vce, groups=vce['qid']).fit()
    conf_params = conf_model.params
    conf_bse = conf_model.bse
    
    print(f"Intercept: {conf_params['Intercept']:.4f} (SE {conf_bse['Intercept']:.4f})")
    print(f"region[T.Europe]: {conf_params['C(region)[T.Europe]']:.4f} (SE {conf_bse['C(region)[T.Europe]']:.4f})")
    print(f"z = {conf_params['C(region)[T.Europe]']/conf_bse['C(region)[T.Europe]']:.2f}")
    
    # Group variance
    if hasattr(conf_model, 'cov_re') and conf_model.cov_re is not None:
        print(f"Group variance (qid): {conf_model.cov_re.iloc[0,0]:.4f}")
    else:
        print("Group variance: not available")
        
except Exception as e:
    print(f"Mixed model failed: {e}")

print("\nDone.")
