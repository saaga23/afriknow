#!/usr/bin/env python3
"""Create a 50-item GM-only pilot subset (25 Africa + 25 Europe)."""

import json
import random

with open('phase2_data/afriknow_gm_only_v3.json', encoding='utf-8') as f:
    data = json.load(f)

items = data['items']
africa = [it for it in items if it['region'] == 'Africa']
europe = [it for it in items if it['region'] == 'Europe']

random.seed(42)
af_sample = random.sample(africa, 25)
eu_sample = random.sample(europe, 25)
pilot = af_sample + eu_sample

# Reindex with item_idx
for i, it in enumerate(pilot):
    it['item_idx'] = i
    it['qid'] = it['id']

print(f"Africa: {len([x for x in pilot if x['region']=='Africa'])}")
print(f"Europe: {len([x for x in pilot if x['region']=='Europe'])}")
print(f"Total: {len(pilot)}")
print()
print('First 3 Africa ids:')
for it in pilot[:3]:
    print(f"  {it['id']} ({it['region']})")
print('First 3 Europe ids:')
for it in pilot[25:28]:
    print(f"  {it['id']} ({it['region']})")

# Save as sampled items
output = {"seed": 42, "n_africa": 25, "n_europe": 25, "total": 50, "items": pilot}
with open('annotator_pipeline/outputs/02_pilot_50_items.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\nSaved to annotator_pipeline/outputs/02_pilot_50_items.json")
