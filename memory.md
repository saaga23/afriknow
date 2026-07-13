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
