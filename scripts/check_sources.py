import json
for fn in ['phase2_data/afriknow_pilot_gm_only_v3.json', 'phase2_data/afriknow_source_annotated_full_v3.json']:
    with open(fn, encoding='utf-8') as f:
        data = json.load(f)
    items = data.get('items', data) if isinstance(data, dict) else data
    if isinstance(items, dict):
        items = list(items.values())
    print(f'{fn}: {len(items)} items')
    if len(items) > 0:
        print(f'  First keys: {list(items[0].keys())[:8]}')
        print(f'  Region sample: {items[0].get("region")}')
        regions = {}
        for it in items:
            r = it.get('region', 'Unknown')
            regions[r] = regions.get(r, 0) + 1
        print(f'  Region distribution: {regions}')
