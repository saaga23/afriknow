import json
with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data.get('items', data) if isinstance(data, dict) else data
if isinstance(items, dict):
    items = list(items.values())
print(f'Total items: {len(items)}')
print(f'First item keys: {list(items[0].keys())}')
print('Sample items:')
for it in items[:3]:
    print(f'  id={it.get("id","?")[:60]:60s} region={it.get("region")} a={it.get("a","MISSING")} answer={it.get("answer","MISSING")}')

# Check if there's any 'a' or 'answer' field anywhere
has_a = sum(1 for it in items if 'a' in it)
has_answer = sum(1 for it in items if 'answer' in it)
print(f'Items with "a" field: {has_a}')
print(f'Items with "answer" field: {has_answer}')

# Check IDs for overlap with 180-item dataset
with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    gm_data = json.load(f)
gm_ids = {it['id'] for it in gm_data['items']}
full_ids = {it['id'] for it in items}
overlap = gm_ids & full_ids
print(f'Overlap with 180-item GM-only: {len(overlap)} items')
print(f'IDs only in 180-item: {len(gm_ids - full_ids)}')
print(f'IDs only in 817-item: {len(full_ids - gm_ids)}')
