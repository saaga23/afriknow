#!/usr/bin/env python3
"""Interactive test of first item in resume dataset."""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_resume_817 as runner

# Load items manually
SAMPLED_JSON = Path(__file__).resolve().parent / "outputs" / "02_sampled_items_resume.json"
with open(SAMPLED_JSON, encoding="utf-8-sig") as f:
    items = json.load(f)["items"]

print(f"Items loaded: {len(items)}")
print(f"Active models: {[m[1] for m in runner.MODELS]}")

idx = 0
item = items[idx]
global_idx = idx + runner.RESUME_OFFSET
print(f"\nProcessing item {global_idx} (idx={idx})")
print(f"Question: {item['q'][:100]}...")

for model_id, nick, temp, max_tok in runner.MODELS:
    print(f"\n  Model: {nick}")
    
    print("    Greedy call...")
    t0 = time.time()
    try:
        c = runner.chat_complete(model_id, runner.build_mcqa_prompt(item), temp, max_tok, "greedy")
        pred = runner.parse_letter(c)
        print(f"    Result: {pred} ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    ERROR: {e}")
        continue
    
    print("    VCE call...")
    t0 = time.time()
    try:
        vc = runner.chat_complete(model_id, runner.build_vce_prompt(item, pred), 0.0, 512, "vce")
        vce = runner.extract_conf(vc)
        print(f"    Result: {vce} ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"    ERROR: {e}")

print("\nDone with first item.")
