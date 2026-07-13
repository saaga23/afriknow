import json
with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    data = json.load(f)
items = data['items']
print(f'Total items: {len(items)}')
print(f'First item keys: {list(items[0].keys())}')
print(f'Item 0 region: {items[0].get("region")}')
print(f'Item 0 cat: {items[0].get("cat")}')
print(f'Item 0 diff: {items[0].get("diff")}')
print(f'Item 0 id: {items[0].get("id")}')
print('Sample items:')
for it in items[:5]:
    print(f'  id={it.get("id","?")[:50]:50s} a={it.get("a","MISSING")} answer={it.get("answer","MISSING")}')
    
# Check all possible 'a' values
a_vals = set()
for it in items:
    a_vals.add(it.get('a'))
print(f'Unique a values: {sorted(a_vals)}')
