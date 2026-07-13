import pandas as pd
import json

print('=== PILOT OUTPUT AUDIT ===')
df = pd.read_csv('annotator_pipeline/outputs/pilot_or_outputs.csv')

print(f'Total rows: {len(df)}')
print(f'Columns: {list(df.columns)}')
print(f'Unique items: {df.id.nunique()}')
print(f'Unique models: {df.model.nunique()}')
print(f'Models: {sorted(df.model.unique())}')
print(f'Purposes: {sorted(df.purpose.unique())}')

print()
greedy = df[df.purpose=='greedy']
vce = df[df.purpose=='vce']
print(f'Greedy rows: {len(greedy)}')
print(f'VCE rows: {len(vce)}')

print()
pf_greedy = len(greedy[greedy.pred == 'X'])
pf_vce = len(vce[vce.pred == 'X'])
print(f'Parse failures (pred=X):')
print(f'  Greedy: {pf_greedy}')
print(f'  VCE: {pf_vce}')

print()
print('Correct counts:')
print(f'  Greedy correct: {greedy.correct.sum()}/{len(greedy)} ({greedy.correct.mean()*100:.1f}%)')
print(f'  VCE correct: {vce.correct.sum()}/{len(vce)} ({vce.correct.mean()*100:.1f}%)')

print()
print('VCE value stats (should be 0-1 floats):')
print(f'  Null VCE in greedy: {greedy.vce.isna().sum()}')
print(f'  VCE in vce rows: {vce.vce.notna().sum()}/{len(vce)}')
print(f'  VCE min: {vce.vce.min()}')
print(f'  VCE max: {vce.vce.max()}')
print(f'  VCE mean: {vce.vce.mean():.3f}')
unique_vces = sorted(vce.vce.dropna().unique())
print(f'  VCE unique count: {len(unique_vces)}')
print(f'  VCE sample unique: {unique_vces[:20]}')

print()
print('Cost stats:')
print(f'  Total cost: ${df.cost_usd.sum():.4f}')
cost_per_item = df.groupby('id').cost_usd.sum()
print(f'  Cost per item (avg): ${cost_per_item.mean():.6f}')
print(f'  Cost per item (max): ${cost_per_item.max():.6f}')
print('  Cost by model:')
cost_by_model = df.groupby('model').cost_usd.sum().sort_values()
for m, c in cost_by_model.items():
    print(f'    {m}: ${c:.4f}')

print()
print('Token stats:')
print(f'  Avg input tokens: {df.input_tokens.mean():.0f}')
print(f'  Avg output tokens: {df.output_tokens.mean():.0f}')
print(f'  Max input tokens: {df.input_tokens.max()}')
print(f'  Max output tokens: {df.output_tokens.max()}')

print()
print('Region balance:')
print(df.groupby('region').id.nunique())

print()
print('Sample VCE rows:')
vce_sample = vce[['model','id','vce','pred','correct']].head(10)
print(vce_sample.to_string())

print()
print('=== CHECKING FOR BUGS ===')

# Bug 1: VCE should be float 0-1, not integer strings
if vce.vce.dtype == object:
    print('WARNING: VCE column is object type, not float. May contain strings.')
    non_numeric = vce[pd.to_numeric(vce.vce, errors='coerce').isna() & vce.vce.notna()]
    if len(non_numeric) > 0:
        print(f'  Non-numeric VCE values: {non_numeric.vce.unique()[:10]}')
else:
    print('OK: VCE column is numeric')

# Bug 2: All 4 models should have 50 items each
for m in df.model.unique():
    items_for_model = df[df.model == m].id.nunique()
    rows_for_model = len(df[df.model == m])
    print(f'Model {m}: {items_for_model} items, {rows_for_model} rows')
    if items_for_model != 50:
        print(f'  WARNING: Expected 50 items, got {items_for_model}')
    if rows_for_model != 100:
        print(f'  WARNING: Expected 100 rows (greedy+vce), got {rows_for_model}')

# Bug 3: Check cocoa_fixed values
print()
print('cocoa_fixed stats in VCE rows:')
print(vce.cocoa_fixed.describe())

print()
print('=== 1000-ITEM SCALING ESTIMATE ===')
# Current pilot: 50 items, 4 models, 2 purposes = 400 rows
# For 1000 items with 7 models:
# 1000 items * 7 models * 2 purposes = 14,000 rows
# Cost per 7-model item = cost_per_item * 3 (for 3 more open models)
# We only have 4 closed models cost data
closed_cost_per_item = df.groupby('id').cost_usd.sum().mean()
print(f'Current closed cost per item (4 models): ${closed_cost_per_item:.6f}')
print(f'Estimated closed cost for 1000 items: ${closed_cost_per_item * 1000:.2f}')

# Modal costs
modal_costs = {
    'llama-3.3-70b': 0.10 * 2 + 0.32 * 2,  # input + output per 1k tokens, need to estimate
    'qwen3-235b': 0.09 * 2 + 0.10 * 2,
    'deepseek-v3.2': 0.2288 * 2 + 0.3432 * 2,
}
# Actually let's estimate based on token counts
avg_input = df.input_tokens.mean()
avg_output = df.output_tokens.mean()
print(f'Average input tokens per purpose: {avg_input:.0f}')
print(f'Average output tokens per purpose: {avg_output:.0f}')
print(f'Total tokens per item (2 purposes): {avg_input + avg_output:.0f}')

print()
print('=== AUDIT COMPLETE ===')
