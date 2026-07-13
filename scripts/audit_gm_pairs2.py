import json
from collections import Counter

with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data.get('items', data) if isinstance(data, dict) else data
if isinstance(items, dict):
    items = list(items.values())

gm_items = [it for it in items if it.get('group', '').startswith('GM_')]
print('Sample GM item IDs:')
for it in gm_items[:20]:
    print(f'  {it["id"]:60s} region={it["region"]:6s} group={it["group"]}')

# Check if there's a pattern for pairing
ids = [it['id'] for it in gm_items]
# Maybe pair by stripping region prefix?
base_ids = []
for id_ in ids:
    parts = id_.split('-')
    if len(parts) >= 4 and parts[0] == 'GM' and parts[1] in ('AF', 'EU'):
        base = '-'.join(parts[2:])  # high_school_world_history-test-67
        base_ids.append((id_, base, parts[1]))
    else:
        base_ids.append((id_, id_, '?'))

from collections import defaultdict
pairs = defaultdict(list)
for id_, base, region in base_ids:
    pairs[base].append((id_, region))

matched = {k: v for k, v in pairs.items() if len(v) == 2 and any(r=='Africa' for _, r in v) and any(r=='Europe' for _, r in v)}
print(f'\nMatched pairs by base ID: {len(matched)}')
for k in list(matched.keys())[:10]:
    print(f'  {k}: {matched[k]}')
