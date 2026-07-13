import json
from collections import Counter, defaultdict

with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data.get('items', data) if isinstance(data, dict) else data
if isinstance(items, dict):
    items = list(items.values())

print(f'Total items: {len(items)}')

# Group by prefix (GM vs non-GM)
gm_items = [it for it in items if it.get('group', '').startswith('GM_')]
non_gm = [it for it in items if not it.get('group', '').startswith('GM_')]
print(f'GM items: {len(gm_items)}')
print(f'Non-GM items: {len(non_gm)}')

# In GM items, check Africa vs Europe balance
print(f'GM Africa: {sum(1 for it in gm_items if it.get("region") == "Africa")}')
print(f'GM Europe: {sum(1 for it in gm_items if it.get("region") == "Europe")}')

# Show GM group distribution
gm_groups = Counter(it.get('group') for it in gm_items)
print('GM groups:')
for g, c in sorted(gm_groups.items()):
    print(f'  {g}: {c}')

# For GM-only, we need matched pairs by cat (subject) + diff
# Extract base subject from ID: GM-{region}-{cat}-test-{num}
# Or use group + cat + diff to match

# Let's see if we can find matched pairs by parsing IDs
def base_id(item_id):
    # GM-AF-high_school_world_history-test-67 -> GM-high_school_world_history-test
    parts = item_id.split('-')
    if len(parts) >= 4 and parts[0] == 'GM':
        # parts[0]=GM, parts[1]=AF/EU, parts[2]=cat, parts[3]=test, parts[4]=num
        return '-'.join(parts[:4])
    return item_id

# Count how many have Africa+Europe pairs
pairs = defaultdict(list)
for it in gm_items:
    b = base_id(it['id'])
    pairs[b].append(it)

paired = {k: v for k, v in pairs.items() if len(v) == 2 and any(x['region']=='Africa' for x in v) and any(x['region']=='Europe' for x in v)}
print(f'Matched GM pairs (Africa+Europe): {len(paired)}')

# Show some examples
for k in list(paired.keys())[:5]:
    print(f'  {k}: {[it["region"] for it in paired[k]]}')

# Count Africa/Europe in pairs
af_pairs = sum(1 for v in paired.values() if any(x['region']=='Africa' for x in v))
eu_pairs = sum(1 for v in paired.values() if any(x['region']=='Europe' for x in v))
print(f'Africa items in pairs: {af_pairs}')
print(f'Europe items in pairs: {eu_pairs}')

# For 1000 GM-only items, we need 500 Africa + 500 Europe
# Let's see what's available in the 817 dataset
print(f'\nFor 1000 GM-only items (500 AF + 500 EU):')
print(f'  Available in 817: {len(paired) * 2} items ({len(paired)} pairs)')
print(f'  Available Africa: {sum(1 for v in paired.values() for x in v if x["region"]=="Africa")}')
print(f'  Available Europe: {sum(1 for v in paired.values() for x in v if x["region"]=="Europe")}')
