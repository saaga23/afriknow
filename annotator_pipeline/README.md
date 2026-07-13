# AfriKnow Annotator Pipeline — Code Trail & Reproducibility

This directory implements the **human-annotator validation pipeline** for the AfriKnow
source-aware calibration audit. It is built directly on the latest production code
(`phase4b_gm_only_run.ipynb` runner + `phase4b_v18_analysis.py` analysis, both dated
2026-06-20/22) and reuses the same hardened patterns: output-constrained prompts,
preflight checks, cost-cap tracking, checkpointing, reserve substitution, and raw-output
forensics.

## Goal

Produce a **reviewer-proof, hallucination-resistant** annotator study that:
1. Computes a statistically justified **minimum sample size** (60 Africa / 60 Europe).
2. Draws a **stratified, reproducible** sample (excludes the 21 flagged content-label mismatches).
3. Runs **5 models** (OpenRouter + Modal lanes) on the sample with full cost tracking.
4. Generates a **blinded annotator interface** (model identities + regions hidden).
5. Compares **annotator judgments vs model outputs** with region-stratified metrics.
6. Emits an **append-only audit trail** (SHA256 hashes + UTC timestamps) for every artifact.

## Phases

| Phase | Script | Purpose | Key output |
|-------|--------|---------|------------|
| 01 | `01_power_analysis.py` | Min sample size (power + ICC + conference floors) | `01_power_analysis_report.md` |
| 02 | `02_sample_design.py` | Stratified 60/60 sample, seed=42, exclude flagged | `02_sampled_items.json` |
| 03 | `03_model_runner.py` | 5-model evaluation (OpenRouter + Modal) | `03_model_outputs.csv`, `03_cost_history.csv` |
| 04 | `04_annotator_interface.py` | Blinded CSV for human raters | `04_annotator_interface.csv`, `04_blinding_key.json` |
| 05 | `05_audit_trail.py` | Append-only provenance logger (used by orchestrator) | `05_audit_trail.jsonl` |
| 06 | `06_annotator_analysis.py` | Annotator-vs-model agreement metrics | `06_annotator_analysis_report.md` |

## Run

```bash
# Full pipeline (needs OPENROUTER_API_KEY in env for real Phase 3)
python run_pipeline.py

# Validate without API calls (synthetic Phase 3 outputs)
python run_pipeline.py --dry-run
```

Phase 3 requires `OPENROUTER_API_KEY` for the closed models (GPT-4o-mini, Claude-3-Haiku).
The open models (DeepSeek-V3.2, Qwen3-235B, Llama-3.3-70B) are configured to run via
Modal serverless GPUs in production; the runner falls back to OpenRouter for the same
model IDs if Modal is not wired, keeping the pipeline single-entry.

## Code Trail (anti-hallucination)

Every pipeline action is appended to `outputs/05_audit_trail.jsonl` with:
- UTC ISO-8601 timestamp
- phase / action label
- **SHA256 of every input and output file** + byte size
- frozen config snapshot (`config: snapshot` event at pipeline start)
- Python version

This makes every number in the manuscript traceable to: (a) the exact dataset version,
(b) the exact script version, (c) the exact model IDs/prices, and (d) the wall-clock time
it was produced. A reviewer (or an auditing agent) can replay the trail and verify hashes.

## Model slate

| Role | Provider | Model ID |
|------|----------|----------|
| Closed (cheap) | OpenRouter | `openai/gpt-4o-mini` |
| Closed (cheap) | OpenRouter | `anthropic/claude-3-haiku` |
| Open | Modal / OpenRouter | `deepseek/deepseek-v3.2` |
| Open | Modal / OpenRouter | `qwen/qwen3-235b-a22b-2507` |
| Open | Modal / OpenRouter | `meta-llama/llama-3.3-70b-instruct` |

Budget: Phase 3 on 120 items × 5 models × 2 calls ≈ **$0.16**, well within the
$9/mo OpenRouter + $10/mo Modal cap.

## Notes

- `04_blinding_key.json` links blinded `Family-*` labels to real model IDs. **Never share
  it with annotators** — the annotator interface CSV is already stripped of region/model/gold.
- The annotator interface CSV ships with empty `annotator_*` columns for raters to fill.
  Re-run `06_annotator_analysis.py` after annotations to regenerate the agreement report.
- Blinding integrity: regions and model identities are removed from the interface; only
  the rater sees `Family-A..E` and the item text. The blinding key reconstructs mapping
  post-hoc for analysis only.
