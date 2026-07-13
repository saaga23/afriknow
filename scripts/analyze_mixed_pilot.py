import pandas as pd

df = pd.read_csv('annotator_pipeline/outputs/03_openrouter_outputs_mixed_pilot.csv')
print('Rows:', len(df))
print('Items:', df['id'].nunique())
print('Models:', df['model'].unique().tolist())
print('Regions:', df['region'].unique().tolist())

vce = df[df['purpose'] == 'vce']
print('\n=== VCE Summary ===')
print(vce.groupby(['region', 'correct'])['vce'].agg(['mean', 'count']))

wrong = vce[vce['correct'] == 0]
print('\n=== Wrong-answer VCE by region ===')
for region, grp in wrong.groupby('region'):
    print(f'{region}: mean={grp["vce"].mean():.3f}, n={len(grp)}')

print('\n=== Accuracy by region ===')
greedy = df[df['purpose'] == 'greedy']
for region, grp in greedy.groupby('region'):
    print(f'{region}: acc={grp["correct"].mean():.3f}, n={len(grp)}')
