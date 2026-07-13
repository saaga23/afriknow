import json
from collections import Counter, defaultdict

with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data['items']

print('Sample IDs from 180-item GM-only:')
for it in items[:20]:
    print(f'  {it["id"]:60s} region={it["region"]:6s} group={it["group"]}')

# Check base IDs
base_ids = []
for it in items:
    id_ = it['id']
    parts = id_.split('-')
    if len(parts) >= 4 and parts[0] == 'GM' and parts[1] in ('AF', 'EU'):
        base = '-'.join(parts[2:])  # high_school_world_history-test-67
        base_ids.append((id_, base, parts[1], it['region']))
    else:
        base_ids.append((id_, id_, '?', it['region']))

pairs = defaultdict(list)
for id_, base, prefix, region in base_ids:
    pairs[base].append((id_, prefix, region))

matched = {k: v for k, v in pairs.items() if len(v) == 2 and any(r=='Africa' for _, _, r in v) and any(r=='Europe' for _, _, r in v)}
print(f'\nMatched pairs in 180-item GM-only: {len(matched)}')
for k in list(matched.keys())[:10]:
    print(f'  {k}: {matched[k]}')
