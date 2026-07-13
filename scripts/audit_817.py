import json
with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data.get('items', data) if isinstance(data, dict) else data
if isinstance(items, dict):
    items = list(items.values())

print(f'Total 817 items: {len(items)}')
regions = {}
for it in items:
    r = it.get('region', 'Unknown')
    regions[r] = regions.get(r, 0) + 1
print('Region distribution in 817:')
for r, c in sorted(regions.items()):
    print(f'  {r}: {c}')

# Check group/source fields
sources = {}
groups = {}
for it in items:
    s = it.get('source', 'Unknown')
    g = it.get('group', 'Unknown')
    sources[s] = sources.get(s, 0) + 1
    groups[g] = groups.get(g, 0) + 1
print('Sources:')
for s, c in sorted(sources.items(), key=lambda x: -x[1]):
    print(f'  {s}: {c}')
print('Groups:')
for g, c in sorted(groups.items(), key=lambda x: -x[1]):
    print(f'  {g}: {c}')

# Check for duplicate IDs
ids = [it['id'] for it in items]
from collections import Counter
dupes = {k: v for k, v in Counter(ids).items() if v > 1}
print(f'Duplicate IDs: {len(dupes)}')
if dupes:
    for k, v in list(dupes.items())[:5]:
        print(f'  {k}: {v} times')
