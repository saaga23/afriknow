import json
from collections import Counter, defaultdict

with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    gm_data = json.load(f)
with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    full_data = json.load(f)

gm_items = gm_data['items']
full_items = full_data.get('items', full_data) if isinstance(full_data, dict) else full_data
if isinstance(full_items, dict):
    full_items = list(full_items.values())

gm_ids = {it['id'] for it in gm_items}
print(f'180 GM-only items: {len(gm_items)}')

# Find GM-only items in 817 that are NOT in the 180 set
full_gm = [it for it in full_items if it.get('group', '').startswith('GM_')]
print(f'817 GM items: {len(full_gm)}')
extra_gm = [it for it in full_gm if it['id'] not in gm_ids]
print(f'Extra GM items in 817: {len(extra_gm)}')

# Now try to build the LARGEST possible GM-only set by:
# 1. Starting with all items from 180 set
# 2. Adding extra items from 817 that can be matched
# 3. Matching by (cat, diff, cs) where possible, then falling back to (cat), then (cat, diff)

all_af = [it for it in gm_items if it['region'] == 'Africa']
all_eu = [it for it in gm_items if it['region'] == 'Europe']
print(f'\nBase: {len(all_af)} Africa + {len(all_eu)} Europe = {len(gm_items)} items')

# Add extra from 817
extra_af = [it for it in extra_gm if it['region'] == 'Africa']
extra_eu = [it for it in extra_gm if it['region'] == 'Europe']
print(f'Extra available: {len(extra_af)} Africa + {len(extra_eu)} Europe')

# Strategy: use ALL Africa items, then match with Europe by strata
combined_af = all_af + extra_af
combined_eu = all_eu + extra_eu
print(f'Combined pool: {len(combined_af)} Africa + {len(combined_eu)} Europe')

# Match by (cat, diff, cs)
af_strata = defaultdict(list)
eu_strata = defaultdict(list)
for it in combined_af:
    af_strata[(it['cat'], it['diff'], it['cs'])].append(it)
for it in combined_eu:
    eu_strata[(it['cat'], it['diff'], it['cs'])].append(it)

matched_af = []
matched_eu = []
for key in af_strata:
    eu_list = eu_strata.get(key, [])
    n = min(len(af_strata[key]), len(eu_list))
    if n > 0:
        matched_af.extend(af_strata[key][:n])
        matched_eu.extend(eu_list[:n])

print(f'\nMatched by (cat, diff, cs): {len(matched_af)} Africa + {len(matched_eu)} Europe = {len(matched_af) + len(matched_eu)} items')

# If not enough, relax to (cat, diff)
if len(matched_af) < 450:
    remaining_af = [it for it in combined_af if it not in matched_af]
    remaining_eu = [it for it in combined_eu if it not in matched_eu]
    
    af_by_catdiff = defaultdict(list)
    eu_by_catdiff = defaultdict(list)
    for it in remaining_af:
        af_by_catdiff[(it['cat'], it['diff'])].append(it)
    for it in remaining_eu:
        eu_by_catdiff[(it['cat'], it['diff'])].append(it)
    
    for key in af_by_catdiff:
        if len(matched_af) >= 500:
            break
        eu_list = eu_by_catdiff.get(key, [])
        n = min(len(af_by_catdiff[key]), len(eu_list))
        if n > 0:
            matched_af.extend(af_by_catdiff[key][:n])
            matched_eu.extend(eu_list[:n])
    
    print(f'After relaxing to (cat, diff): {len(matched_af)} Africa + {len(matched_eu)} Europe = {len(matched_af) + len(matched_eu)} items')

# If still not enough, relax to (cat) only
if len(matched_af) < 450:
    remaining_af = [it for it in combined_af if it not in matched_af]
    remaining_eu = [it for it in combined_eu if it not in matched_eu]
    
    af_by_cat = defaultdict(list)
    eu_by_cat = defaultdict(list)
    for it in remaining_af:
        af_by_cat[it['cat']].append(it)
    for it in remaining_eu:
        eu_by_cat[it['cat']].append(it)
    
    for key in af_by_cat:
        if len(matched_af) >= 500:
            break
        eu_list = eu_by_cat.get(key, [])
        n = min(len(af_by_cat[key]), len(eu_list))
        if n > 0:
            matched_af.extend(af_by_cat[key][:n])
            matched_eu.extend(eu_list[:n])
    
    print(f'After relaxing to (cat) only: {len(matched_af)} Africa + {len(matched_eu)} Europe = {len(matched_af) + len(matched_eu)} items')

print(f'\nFinal GM-only max: {len(matched_af) + len(matched_eu)} items ({len(matched_af)} Africa + {len(matched_eu)} Europe)')
print('\nThis is the TRUE maximum GM-only available from all sources.')
print('Note: Relaxed matching (cat-only) includes items with different difficulties/CS labels.')
