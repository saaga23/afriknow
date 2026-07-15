import json
from pathlib import Path

paths = [
    Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo\annotator_pipeline\outputs\02_mixed_source_180_items.json'),
    Path(r'C:\Users\USER\Downloads\Revamp\afriknow-repo\02_mixed_source_180_items.json'),
]

for p in paths:
    if p.exists():
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        items = data['items']
        flagged = [it for it in items if it.get('flagged', False) or it.get('content_label_mismatch', False)]
        print(f'Found: {p}')
        print(f'Total items: {len(items)}')
        print(f'Flagged: {len(flagged)} ({len(flagged)/len(items):.1%})')
        if flagged:
            print('Sample flagged items:')
            for it in flagged[:3]:
                print(f'  {it.get("id", "?")} - {it.get("region", "?")}')
        break
else:
    print('Items file not found in expected locations')
