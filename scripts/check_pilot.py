import pandas as pd
df = pd.read_csv('annotator_pipeline/outputs/pilot_or_outputs.csv')
greedy = df[df['purpose']=='greedy']
print('Prediction distribution:')
print(greedy['pred'].value_counts())
print()
print('Correct letter distribution:')
print(greedy['correct_letter'].value_counts())
print()
print('Sample wrong predictions:')
wrong = greedy[greedy['correct']==0].head(5)
for _, row in wrong.iterrows():
    print(f"  {row['model']} | {row['id'][:40]}... | pred={row['pred']} gold={row['correct_letter']}")
