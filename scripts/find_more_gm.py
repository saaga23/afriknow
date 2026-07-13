import json
from collections import Counter, defaultdict

with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data.get('items', data) if isinstance(data, dict) else data
if isinstance(items, dict):
    items = list(items.values())

# Filter to Global-MMLU only
gmmlu_items = [it for it in items if it.get('source') == 'Global-MMLU (ACL 2025)']
print(f'Global-MMLU items in 817: {len(gmmlu_items)}')
af_gm = [it for it in gmmlu_items if it['region'] == 'Africa']
eu_gm = [it for it in gmmlu_items if it['region'] == 'Europe']
print(f'  Africa GM: {len(af_gm)}')
print(f'  Europe GM: {len(eu_gm)}')

# Try matching by (cat, diff) only, ignoring cs
af_by_catdiff = defaultdict(list)
eu_by_catdiff = defaultdict(list)
for it in af_gm:
    af_by_catdiff[(it['cat'], it['diff'])].append(it)
for it in eu_gm:
    eu_by_catdiff[(it['cat'], it['diff'])].append(it)

pairs_catdiff = []
for key in af_by_catdiff:
    n = min(len(af_by_catdiff[key]), len(eu_by_catdiff.get(key, [])))
    if n > 0:
        pairs_catdiff.extend([key] * n)

print(f'\nMatched pairs by (cat, diff): {len(pairs_catdiff)} pairs = {len(pairs_catdiff)*2} items')
print(f'  Africa items: {sum(len(af_by_catdiff[k]) for k in pairs_catdiff)}')
print(f'  Europe items: {sum(len(eu_by_catdiff[k]) for k in pairs_catdiff)}')

# Try matching by cat only
af_by_cat = defaultdict(list)
eu_by_cat = defaultdict(list)
for it in af_gm:
    af_by_cat[it['cat']].append(it)
for it in eu_gm:
    eu_by_cat[it['cat']].append(it)

pairs_cat = []
for key in af_by_cat:
    n = min(len(af_by_cat[key]), len(eu_by_cat.get(key, [])))
    if n > 0:
        pairs_cat.extend([key] * n)

print(f'\nMatched pairs by cat only: {len(pairs_cat)} pairs = {len(pairs_cat)*2} items')

# Show available items per cat
print('\nItems per category (Africa GM / Europe GM):')
for cat in sorted(af_by_cat.keys()):
    af = len(af_by_cat[cat])
    eu = len(eu_by_cat.get(cat, []))
    print(f'  {cat}: AF={af}, EU={eu}, min={min(af, eu)} pairs')

# Now check if 180-item set is just a subset of these
with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    gm_data = json.load(f)
gm_ids = {it['id'] for it in gm_data['items']}
af_gm_ids = {it['id'] for it in af_gm}
eu_gm_ids = {it['id'] for it in eu_gm}
print(f'\n180 GM-only IDs in 817 Africa GM: {len(gm_ids & af_gm_ids)}')
print(f'180 GM-only IDs in 817 Europe GM: {len(gm_ids & eu_gm_ids)}')
