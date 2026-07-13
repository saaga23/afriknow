# Mixed-Source Contrast Experiment Design

## Objective

Demonstrate the source-confounding thesis **within one coherent study** by comparing:
1. **GM-only condition:** 180 Global-MMLU items (90 Africa / 90 Europe)
2. **Mixed-source condition:** 180 items with mixed Global-MMLU + AfriMMLU sources (90 Africa / 90 Europe)

Both conditions use the **same 7 models** and **same protocol**.

## Hypothesis

- H1: In the GM-only condition, Africa and Europe accuracy are equal (null)
- H2: In the mixed-source condition, apparent Africa-Europe disparities emerge
- H3: The disparity in H2 is explained by source mixing, not by intrinsic regional differences

## Item Selection

### GM-only Condition (Current)
- Source: `02_gm_only_180_items.json`
- 90 Africa + 90 Europe, all Global-MMLU
- Matched by (category, difficulty, cultural-sensitivity)

### Mixed-Source Condition (New)
- Source: `02_expanded_globalmmlu_items.json` + AfriMMLU items
- 90 Africa items: mix of Global-MMLU and AfriMMLU
- 90 Europe items: Global-MMLU only (control)
- Matching: same categories and difficulties as GM-only set

## Models

Same 7 models as GM-only run:
- **Closed (OpenRouter):** claude-sonnet-4.6, gpt-4o-mini, gpt41-nano, gemini-2.5-flash-lite
- **Open (Modal):** deepseek-v3.2, gemma-4-31b, llama-3.3-70b

## Protocol

1. Run greedy MCQA on all 180 mixed-source items
2. Run VCE on all 180 mixed-source items
3. Merge with GM-only results using `schema.py`
4. Compute accuracy, ECE, Brier, CHR, H3 for both conditions
5. Test whether the Africa-Europe disparity interacts with source condition

## Statistical Test

- **Primary:** Mixed-effects logistic regression with interaction:
  `correct ~ region * source_condition + (1 | qid)`
- **Secondary:** Equivalence test for H3 within each condition separately

## Expected Outcomes

| Condition | Africa Acc | Europe Acc | Disparity |
|---|---|---|---|
| GM-only | ~87% | ~86% | Null (H1 supported) |
| Mixed-source | ~82% | ~88% | Apparent disparity (H2 supported) |

## Cost Estimate

| Lane | Models | Items | Cost |
|---|---|---|---|
| OpenRouter | 4 closed | 180 | ~$0.40 |
| Modal | 3 open | 180 | ~$0.25 (GPU) |
| **Total** | **7** | **360** | **~$0.65** |

## Reproducibility

- All outputs saved to `annotator_pipeline/outputs/03_openrouter_outputs_mixed.csv`
- Manifest includes source_condition tag per row
- Schema validated by `schema.py`
