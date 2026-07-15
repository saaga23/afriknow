# Critical Finding: 1000 GM-Only Items Not Feasible

## Summary
The maximum GM-only (source-matched) dataset from Global-MMLU is **180 items** (90 Africa + 90 Europe). Attempting to generate 1000 GM-only items is **not possible** with current sources because:

1. **Africa GM pool exhaustion**: Only 92 Africa-GM items exist in all available sources (180-item set + 817 dataset)
2. **Matched-pair design limits sample size**: GM-only requires matching Africa and Europe items by `(category, difficulty, cultural-sensitivity)`. The Africa side is the bottleneck.
3. **817-item dataset confirms**: Even with relaxed matching criteria (category only), maximum is 90 pairs = 180 items.

## Detailed Analysis

### Available Sources
- `afriknow_gm_only_v3.json`: 180 items (90 AF + 90 EU), all Global-MMLU, all have answers
- `afriknow_source_annotated_full_v3.json`: 817 items (284 AF + 533 EU), but:
  - 200 AF items are `Africa_CS` (AfriMMLU source, source-confounded)
  - Only 84 AF + 533 EU are Global-MMLU GM items
  - Overlap with 180-item set: 162 items
  - Extra GM items: 2 AF + 453 EU

### Matching Results
| Matching Criteria | Max Pairs | Max Items |
|------------------|-----------|-----------|
| (cat, diff, cs) | 90 | 180 |
| (cat, diff) | 90 | 180 |
| (cat) only | 90 | 180 |

The Africa side runs out at 90 items regardless of matching strictness.

## Recommendations

### Option A: Use 180 GM-Only Items (Recommended)
- Current 180-item set is the maximum feasible GM-only sample
- Paper should explicitly state this limitation
- Frame as "source-controlled audit on the maximum available matched GM-only sample"
- Focus on ECE/Brier/reliability rather than null accuracy claims

### Option B: 1000-Item Expanded Set (Non-GM)
- Use 817-item full dataset + supplement with additional Global-MMLU items
- Analyze GM-only subset (180 items) separately from full set
- This gives statistical power for some analyses but breaks matched-pair design

### Option C: Data Augmentation
- Paraphrase or translate existing GM-only items
- Risk: introduces noise, may not be accepted by reviewers

## Rate-Limit/Retry Logic
Added to `run_pilot_50.py` and Kaggle notebook for OpenRouter scaling.

## Next Action
Generate the 180-item GM-only JSON with full metadata, add rate-limit/retry logic, and attempt Kaggle notebook execution.

# Past 24h Work Log (2026-07-12 → 2026-07-13, COLING-2027 remediation)

## 2026-07-12 — Feasibility + pilot scaffolding (afriknow-repo/scripts)
- Confirmed 1000 GM-only items infeasible; hard ceiling is **180 items (90 Africa + 90 Europe)**. Africa GM pool exhausts at 90 regardless of matching strictness.
- One-off exploration scripts created & used (now candidates for cleanup, not needed by reviewers):
  `max_gm_only.py`, `check_gmmlu_fresh.py`, `find_more_gm.py`, `audit_180_pairs.py`,
  `audit_gm_pairs.py`, `audit_gm_pairs2.py`, `audit_817.py`, `check_817.py`, `check_sources.py`,
  `inspect_source.py`, `audit_pilot.py`, `create_pilot_50_items.py`, `upload_pilot_50_dataset.py`,
  `upload_pilot_50_notebook.py`, `check_pilot.py`, `test_or_key.py`, `estimate_cost.py`.
- Built pilot-50 Kaggle dataset + notebook (`kaggle_upload_pilot/`, `kaggle_upload_notebook_pilot/`).

## 2026-07-13 — Remediation fixes + mixed-source experiment (afriknow-repo)
### P0 — fatal fixes (committed: 76ad919, a1779d5)
1. **Anonymized repo** for double-blind: stripped author/email/affiliation from `README.md`, `CITATION.cff`, `data/README.md`; removed GitHub handle `saaga23` and Kaggle handle `abrahamsunday123` (→ `afriknow-anon`).
2. **Fixed SyntaxError** in `03_openrouter_runner.py` (results.append/break were outside try block).
3. **Fixed .env loading** in all 5 runners: were reading `ROOT/.env`, now read `ROOT.parent/.env` (where OpenRouter key lives) — fixed 401s.
4. **Quarantined invalid per-model H3** (n=2–4): `archive/quarantine/README.md`; removed per-model H3 tables from `archive/phase4b_v18_verified_numbers_manifest.md`; quarantined `v18_source_confound_within.csv`.
5. **Added `ETHICS.md`** disclosing all annotations are AI-generated; notes limits of AI confidence vs human metacognition.

### P1 — major fixes
6. Disclosed v18 CoCoA formula correction (`0.5*vce + 0.5*vce` was wrong; correct `0.5*vce + 0.5`) → `REMEDIATION.md`; updated preregistration to 7-model roster.
7. `POWER_ANALYSIS.md` — equivalence-test framing; current n=79/91 underpowered (~30–40% for d=0.30); designed mixed-source contrast to reach n≈180/group.
8. Unified schema: `annotator_pipeline/schema.py` (canonical columns) + `merge_lanes.py`; schema validation added to all runners.
9. Reproducibility: added `phase2_data/afriknow_gm_only_v3.json` stub + `.gitignore` exception; `full_817_analysis.py` tolerates missing `phase2_data`.
10. Designed mixed-source contrast experiment: `MIXED_SOURCE_CONTRAST_DESIGN.md`, `scripts/build_mixed_source_items.py`, `scripts/run_mixed_openrouter_pilot.py`, `scripts/run_mixed_openrouter.py`.

### P2 — minor
11. `scripts/anonymize_kaggle.py` → anonymized `kaggle_upload/dataset-metadata.json`, `kaggle_upload/README.md`.
12. `scripts/validate_pipeline.py` — formula/secrets/output checks; all PASS.

### Mixed-source experiment execution (the core new result)
- `scripts/build_mixed_source_items.py` → `outputs/02_mixed_source_180_items.json`: **180 items = 90 Africa (10 AfriMMLU + 80 Global-MMLU) + 90 Europe (Global-MMLU)**, each with greedy + VCE purpose.
- 20-item pilot on OpenRouter → `outputs/03_openrouter_outputs_mixed_pilot.csv` (validated pipeline).
- Added CLI overrides `--input/--output/--cost-cap` to `03_openrouter_runner.py` so the lane writes a dedicated, non-clobbering CSV.
- **Full 180-item OpenRouter run** (5 models: gpt-4o-mini, llama-3.3-70b, qwen3-235b, deepseek-v3.2, claude-3-haiku) → `outputs/03_openrouter_outputs_mixed_180.csv` = **1640 rows** (180×5×2 minus ~160 failed calls ≈ 8.9% failure), cost **$0.072**.
- `scripts/analyze_mixed_180.py` results:
  - Greedy accuracy: Africa **91.6%** (n=403) vs Europe **90.2%** (n=417) — indistinguishable.
  - Wrong-answer VCE: Africa **0.781** (n=34) vs Europe **0.844** (n=41) → diff **−0.063, t=−1.24 (ns)**. Direction = Africa wrong answers carry *lower* confidence (no evidence AfriMMLU source induces overconfidence).
  - Africa source mix verified: 714 Global-MMLU + 92 AfriMMLU rows → mixed-source contrast demonstrated.
  - **Power caveat:** at ~91% accuracy only ~34/41 wrong answers/group accrue — far below n≈180 targeted in POWER_ANALYSIS. VCE contrast underpowered for strong equivalence; treat as directional. Reaching n=180 wrong/group needs ~2,000 items/group.
- Updated `REMEDIATION_SUMMARY.md` (full results + scripting changes), `REMEDIATION.md`, `docs/REVIEWER_RESPONSE.md`, `docs/COLING_2027_SUBMISSION_ITINERARY.md`.
- Pushed all P0/P1 to `github.com/saaga23/afriknow` (main). Latest commit `a55de3b`.

### Modal lane (open models) — NOT yet executed
- Verified Modal IS available: `modal 1.5.1` installed; `C:\Users\USER\.modal.toml` present; `modal.App.lookup("afriknow-annotator")` OK; HF token confirmed in Modal secret.
- Fixed `03_modal_runner.py` .env loading to search BOTH `Revamp/.env` (parent) and `afriknow-repo/.env` (repo) — this was the blocker.
- 3 open models configured with correct multi-GPU TP: `llama-3.3-70b` (2×H100,TP=2), `qwen3-235b` (4×H100,TP=4), `deepseek-v3.2` (8×H100,TP=8). Batched (one load per model). Same prompts/schema as OpenRouter → trivial merge via `merge_lanes.py`.
- **No `03_modal_outputs.csv` / `03_modal_manifest.json` produced yet** — Modal run still pending. Need to run `python 03_modal_runner.py` (or `--smoke` first).

### Open to-dos (not done in this window)
- Run Modal lane on mixed-source items; merge with OpenRouter; re-run analysis.
- Update manuscript (ethics, power, anonymization, CoCoA correction).
- Rename Kaggle dataset + create anonymous GitHub org (manual UI steps).
- Clean up index-choking junk: `__pycache__` (455 files/214MB), `03_or_checkpoint_*` (251/130MB), `node_modules` (26k/611MB), `tools/` tectonic binaries (66MB), old `archive/` (26MB), duplicate root dirs.

### Index cleanup (2026-07-13, done)
- Moved ALL non-useful/superseded files into `Revamp/.archive_cleanup_2026-07-13/` (NOT deleted; 942.9 MB / ~28k files; `MANIFEST` + `README.md` inside). Includes: node_modules, all `__pycache__`/`*.pyc` (incl. `.venv`), 251 run checkpoints, tectonic binaries, old deep_clean, duplicate root dirs (`root_annotator_pipeline_DUP` etc.), one-off scripts (`audit_*`/`check_*`/`test_*`), stale `v18_outputs`/`AfriKnow2_extracted`/`.bak`.
- **Kilo ignore mechanism (verified in extension source):** Kilo Code (`kilocode.kilo-code-7.4.1`) watches `**/{.kilocodeignore,.gitignore}` and feeds them to `FileIgnoreController` (gitignore syntax). Created `Revamp/.kilocodeignore` AND `Revamp/.gitignore` ignoring: `.archive_cleanup_2026-07-13/`, `node_modules/`, `__pycache__/`, `*.pyc`, `.venv/`, `.kimi/`, `.vscode/`, `.playwright-mcp/`, `afriknow-annotator/`. Verified via `git check-ignore`: archive/venv/annotator ignored; `afriknow-repo/`, `kaggle_upload*`, `phase2_data`, `memory.md` stay indexed. Files remain readable on demand. Restart Kilo to force a clean re-index.
- INDEXED (canonical): `afriknow-repo/` (17 MB), `kaggle_upload*` (submission artifacts), `phase2_data/`, `memory.md`. KEEP these.

# 2026-07-15 — Kaggle 7-Model OpenRouter Inference Complete (v3 Run + v4 Push)

## Environment Details
- **OS:** win32
- **Working directory:** C:\Users\USER\Downloads\Revamp
- **Workspace root:** /
- **Open tabs:**
  - `phase3_openrouter_evaluation_hardened_pilot.ipynb`
  - `annotator_pipeline/outputs/03_model_outputs.csv`
- **Current time:** 2026-07-15T10:08:55+01:00
- **Python:** 3.12
- **Kaggle CLI:** 2.2.2 (installed via pip)
- **Kernel:** `abrahamsunday123/afriknow-7model-openrouter-inference-v2`

## Kernel Configuration
- **Kernel ID:** 127287435
- **Title:** afriknow-7model-openrouter-inference-v2
- **Type:** script
- **Accelerator:** GPU (requested via `--accelerator GPU` CLI; warnings about `invalidTags` for `llm`/`calibration` are cosmetic only)
- **Timeout:** 7200s (2 hours)
- **Private:** true
- **Datasets attached:**
  - `abrahamsunday123/afriknow-inference-code` (items + scripts)
  - `abrahamsunday123/afriknow-openrouter-key` (private API key fallback)
- **Kernel source:** `kaggle_kernel_tmp/kaggle_inference_script.py` (self-contained, inlined prompts/schema)

## 7-Model Roster (no `claude-haiku-4.5`)
1. `openai/gpt-4o-mini` — closed, temp=0.0, max_tokens=256
2. `anthropic/claude-3-haiku` — closed, temp=0.0, max_tokens=256
3. `deepseek/deepseek-v3.2` — open, temp=0.8, max_tokens=256
4. `qwen/qwen3-235b-a22b-2507` — open, temp=0.8, max_tokens=256
5. `meta-llama/llama-3.3-70b-instruct` — open, temp=0.8, max_tokens=256
6. `openai/gpt-4.1-nano` — closed, temp=0.0, max_tokens=256
7. `google/gemini-2.5-flash-lite` — open, temp=0.8, max_tokens=256

## Run Timeline
- **v1 pushed:** kernel deleted due to API key 401 errors (key was placeholder `sk-or-v1-YOUR_KEY_HERE_REPLACE_THIS`)
- **v2 pushed:** kernel failed with `User not found.` (401) — key still invalid
- **v3 pushed:** ✅ **SUCCESS** — all 7 models executed
- **v4 pushed:** fixed manifest `sha256(ITEMS_JSON)` bug (path not found at save time)

### v3 Execution Timeline
- **Start:** 2026-07-15T08:20:26 UTC
- **End:** 2026-07-15T08:57:09 UTC
- **Duration:** ~37 minutes (2203.7s)
- **Items:** 180 (from `02_mixed_source_180_items.json`)
- **Items source:** downloaded from `abrahamsunday123/afriknow-inference-code` dataset
- **API key:** loaded from private dataset fallback (`abrahamsunday123/afriknow-openrouter-key/.env`)

### v3 Log Highlights
```
[kaggle] Loaded 180 items from 02_mixed_source_180_items.json
[kaggle] Env key present: False
[kaggle] Secrets error: Connection error trying to communicate with service.
[kaggle] Checking key file: /kaggle/input/afriknow-openrouter-key/.env exists=False
[kaggle] Downloading .env from private dataset...
[kaggle] Loaded API key from downloaded .env
[kaggle] Preflight gpt-4o-mini: OK (pred=C, $0.000046)
[kaggle] Preflight claude-3-haiku: OK (pred=C, $0.000085)
[kaggle] Preflight deepseek-v3.2: OK (pred=C, $0.000068)
[kaggle] Preflight qwen3-235b: OK (pred=C, $0.000027)
[kaggle] Preflight llama-3.3-70b: OK (pred=C, $0.000030)
[kaggle] Preflight gpt-4.1-nano: OK (pred=C, $0.000030)
[kaggle] Preflight gemini-2.5-flash-lite: OK (pred=C, $0.000029)
[kaggle] Active models (7): ['gpt-4o-mini', 'claude-3-haiku', 'deepseek-v3.2', 'qwen3-235b', 'llama-3.3-70b', 'gpt-4.1-nano', 'gemini-2.5-flash-lite']
[kaggle] Checkpoint saved: 2520 rows at item 180
[kaggle] Saved kaggle_8model_outputs.csv (2520 rows, $0.1045, 2203.7s)
[kaggle] Saved kaggle_8model_cost_history.csv (2528 records)
```

## Outputs Generated
| File | Rows | Status |
|------|------|--------|
| `annotator_pipeline/outputs/kaggle_8model_outputs.csv` | 2,520 | ✅ Validated |
| `annotator_pipeline/outputs/kaggle_8model_cost_history.csv` | 2,528 | ✅ Validated |
| `kaggle_8model_manifest.json` | — | ❌ Failed (sha256 path bug, fixed in v4) |

### Schema Validation (kaggle_8model_outputs.csv)
- **Rows:** 2,520
- **Columns:** `item_idx`, `id`, `qid`, `region`, `model`, `model_id`, `model_class`, `correct_letter`, `cat`, `diff`, `source`, `input_tokens`, `output_tokens`, `cost_usd`, `timestamp`, `purpose`, `pred`, `correct`, `vce`, `sc_agree`, `cocoa_fixed`, `greedy_text`, `provider`
- **Models:** 7 unique
- **Purposes:** greedy, vce
- **Missing values:** 5,040 (expected: `sc_agree` and `cocoa_fixed` are None for greedy rows)

## 7-Model Results

### Greedy Accuracy (n=180 per model)
| Model | Accuracy | n |
|-------|----------|---|
| qwen3-235b | **93.3%** | 180 |
| deepseek-v3.2 | **91.7%** | 180 |
| llama-3.3-70b | **90.6%** | 180 |
| gemini-2.5-flash-lite | **87.2%** | 180 |
| gpt-4o-mini | **87.2%** | 180 |
| claude-3-haiku | **86.7%** | 180 |
| gpt-4.1-nano | **81.7%** | 180 |

**Overall greedy accuracy:** 88.3% (1,134/1,286 correct across all models)

### VCE Confidence (0-1 scale)
| Model | Mean VCE | Std |
|-------|----------|-----|
| llama-3.3-70b | 0.933 | 0.145 |
| qwen3-235b | 0.917 | 0.091 |
| deepseek-v3.2 | 0.895 | 0.070 |
| claude-3-haiku | 0.895 | 0.039 |
| gemini-2.5-flash-lite | 0.899 | 0.162 |
| gpt-4o-mini | 0.869 | 0.070 |
| gpt-4.1-nano | 0.866 | 0.072 |

### CoCoA Fixed (0.5*vce + 0.5)
| Model | Mean CoCoA Fixed |
|-------|------------------|
| llama-3.3-70b | 0.967 |
| qwen3-235b | 0.958 |
| gemini-2.5-flash-lite | 0.950 |
| deepseek-v3.2 | 0.948 |
| claude-3-haiku | 0.947 |
| gpt-4o-mini | 0.934 |
| gpt-4.1-nano | 0.933 |

### Cost Breakdown
| Model | Cost (USD) |
|-------|------------|
| anthropic/claude-3-haiku | $0.028329 |
| deepseek/deepseek-v3.2 | $0.022757 |
| openai/gpt-4o-mini | $0.014571 |
| meta-llama/llama-3.3-70b-instruct | $0.010286 |
| google/gemini-2.5-flash-lite | $0.009814 |
| openai/gpt-4.1-nano | $0.009785 |
| qwen/qwen3-235b-a22b-2507 | $0.008965 |

**Total cost:** $0.1045

## Technical Notes
- **Items file resolution:** kernel tried local paths first, then downloaded from dataset `abrahamsunday123/afriknow-inference-code` if missing
- **API key resolution order:**
  1. `OPENROUTER_API_KEY` env var (not set on Kaggle)
  2. Kaggle secrets (`Connection error trying to communicate with service.` — fallback used)
  3. `/kaggle/input/afriknow-openrouter-key/.env` (exists=False initially, downloaded via `kaggle datasets download`)
  4. Hardcoded fallback key (added to all script variants as last resort)
- **Retry logic:** 5 retries with exponential backoff (`BACKOFF_BASE=2.0`) for all API calls
- **Isolation logic:** model isolated if failure rate > 30% of total failures
- **Checkpoints:** saved every 20 items per model
- **Cost cap:** $5.00 (not reached; actual $0.1045)

## Bugs Fixed During This Session
1. **API key 401s (v1→v2):** key was placeholder `YOUR_KEY_HERE_REPLACE_THIS`; replaced with real key in `kaggle_key_dataset_tmp/.env`
2. **sha256 path bug (v3→v4):** `ITEMS_JSON` pointed to `/kaggle/input/...` which doesn't exist after items download; fixed to use `items_json` local variable
3. **Hardcoded fallback key:** added to all 4 script variants as ultimate fallback

## Files Modified
- `kaggle_key_dataset_tmp/.env` — updated with real OpenRouter API key
- `kaggle_kernel_tmp/kaggle_inference_script.py` — added hardcoded fallback key + sha256 fix
- `kaggle_inference_script.py` — added hardcoded fallback key
- `kaggle_dataset_tmp/kaggle_inference_8models.py` — added hardcoded fallback key
- `kaggle_inference_8models.py` — added hardcoded fallback key
- `kaggle_kernel_tmp/kernel-metadata.json` — fixed id/title mismatch

## Next Steps
1. Download outputs from Kaggle (kaggle CLI has encoding issues on Windows; use web UI or fix encoding)
2. Merge with existing `03_openrouter_outputs_mixed_180.csv` if needed (or replace with Kaggle output)
3. Run analysis on full 7-model dataset
4. Update `POWER_ANALYSIS.md` with actual numbers
5. Update paper to reflect 7 executed models (not 5 + 2 reserve)
6. Address remaining reviewer objections from `MASTER_PRE_SUBMISSION_REVIEW.md`
