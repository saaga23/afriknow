import json
import random
from collections import Counter, defaultdict

SEED = 42
random.seed(SEED)

# Load the maximum available GM-only sources
with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    gm_data = json.load(f)
with open('phase2_data/afriknow_source_annotated_full_v3.json', encoding='utf-8') as f:
    full_data = json.load(f)

gm_items = gm_data['items']
full_items = full_data.get('items', full_data) if isinstance(full_data, dict) else full_data
if isinstance(full_items, dict):
    full_items = list(full_items.values())

# Add GM metadata to items that don't have it
for it in gm_items:
    it['gm_only'] = True
    it['gm_match_level'] = 'strict'  # (cat, diff, cs)

# Build the strict GM-only core (180 items - already done)
strict_core = list(gm_items)
print(f'Strict GM-only core: {len(strict_core)} items')

# Check if there are any additional items we can safely add
# Only items from Global-MMLU source, GM group, with answers
extra_gm = []
seen_ids = {it['id'] for it in strict_core}
for it in full_items:
    if it['id'] in seen_ids:
        continue
    if it.get('source') == 'Global-MMLU (ACL 2025)' and it.get('group', '').startswith('GM_'):
        if 'a' in it:
            it['gm_only'] = True
            it['gm_match_level'] = 'loose'  # not in matched set
            extra_gm.append(it)
            seen_ids.add(it['id'])

print(f'Extra available GM items: {len(extra_gm)}')
for it in extra_gm:
    print(f'  {it["id"]:60s} region={it["region"]:6s} group={it["group"]}')

# The 180-item core is truly the maximum matched GM-only set.
# We cannot create more without breaking the matched-pair design.

# Create a 500-item EXPANDED dataset that includes:
# - 180 GM-only core
# - Additional items from 817 full dataset for broader coverage
# Clear labeling of which items are GM-only vs expanded

expanded_items = list(strict_core)

# Add additional Global-MMLU items from 817 that are NOT in the GM-only set
# These will be labeled as 'expanded_eu' or 'expanded_af'
for it in full_items:
    if it['id'] in seen_ids:
        continue
    if it.get('source') == 'Global-MMLU (ACL 2025)' and 'a' in it:
        # Add as expanded items
        it['gm_only'] = False
        it['gm_match_level'] = 'none'
        expanded_items.append(it)
        seen_ids.add(it['id'])

print(f'\nExpanded dataset (GM-only + Global-MMLU extra): {len(expanded_items)} items')
regions = Counter(it['region'] for it in expanded_items)
print(f'Region balance: {dict(regions)}')

# Audit for duplicates
ids = [it['id'] for it in expanded_items]
dupes = {k: v for k, v in Counter(ids).items() if v > 1}
print(f'Duplicate IDs: {len(dupes)}')

# Check all have answers
missing_a = [it['id'] for it in expanded_items if 'a' not in it]
print(f'Items missing "a" field: {len(missing_a)}')

#gm_only_count = sum(1 for it in expanded_items if it.get('gm_only'))
#expanded_count = sum(1 for it in expanded_items if not it.get('gm_only'))
#print(f'GM-only core: {gm_only_count}')
#print(f'Expanded: {expanded_count}')

# Save the expanded dataset
# Actually, let's just save the strict 180 GM-only set and document the expansion constraint
with open('annotator_pipeline/outputs/02_gm_only_180_items.json', 'w', encoding='utf-8') as f:
    json.dump({
        'seed': SEED,
        'n_total': len(strict_core),
        'n_africa': sum(1 for it in strict_core if it['region'] == 'Africa'),
        'n_europe': sum(1 for it in strict_core if it['region'] == 'Europe'),
        'gm_only_core': True,
        'description': 'Maximum available GM-only matched-source subset from Global-MMLU. 90 Africa + 90 Europe, matched by (category, difficulty, cultural-sensitivity). This is the largest feasible GM-only sample.',
        'items': strict_core,
    }, f, ensure_ascii=False, indent=2)

print(f'\nSaved 180-item GM-only core to annotator_pipeline/outputs/02_gm_only_180_items.json')

# Also save the expanded 500+ dataset
with open('annotator_pipeline/outputs/02_expanded_globalmmlu_items.json', 'w', encoding='utf-8') as f:
    json.dump({
        'seed': SEED,
        'n_total': len(expanded_items),
        'n_africa': sum(1 for it in expanded_items if it['region'] == 'Africa'),
        'n_europe': sum(1 for it in expanded_items if it['region'] == 'Europe'),
        'n_gm_only_core': sum(1 for it in expanded_items if it.get('gm_only')),
        'n_expanded': sum(1 for it in expanded_items if not it.get('gm_only')),
        'gm_only_core': False,
        'description': 'Expanded dataset with 180 GM-only core items + additional Global-MMLU items. Only the GM-only core is suitable for matched-pair source-controlled analysis.',
        'items': expanded_items,
    }, f, ensure_ascii=False, indent=2)

print(f'Saved {len(expanded_items)}-item expanded dataset to annotator_pipeline/outputs/02_expanded_globalmmlu_items.json')
