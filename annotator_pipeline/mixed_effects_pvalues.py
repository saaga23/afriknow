#!/usr/bin/env python3
"""
Get p-values for mixed-effects confidence model.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo')))

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

OUT_DIR = Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo\annotator_pipeline\outputs')
df = pd.read_csv(OUT_DIR / 'kaggle_8model_outputs.csv')
vce = df[df['purpose'] == 'vce'].copy()

vce['vce_clipped'] = vce['vce'].clip(0.001, 0.999)
vce['logit_vce'] = np.log(vce['vce_clipped'] / (1 - vce['vce_clipped']))

conf_model = smf.mixedlm("logit_vce ~ C(region) + C(model)", vce, groups=vce['qid']).fit()

params = conf_model.params
bse = conf_model.bse

for name in params.index:
    z = params[name] / bse[name]
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    print(f"{name}: coef={params[name]:.4f}, SE={bse[name]:.4f}, z={z:.2f}, p={p:.4f}")
