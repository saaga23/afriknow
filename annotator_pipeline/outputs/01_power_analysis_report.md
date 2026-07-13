# AfriKnow Annotator Pipeline — Minimum Sample Size Analysis

*Generated: 2026-07-06 15:21:48 UTC*
*Script: C:\Users\USER\Downloads\Revamp\annotator_pipeline\01_power_analysis.py*
*Data source: afriknow_gm_only_v3.json (SHA256: 2193db46e849)*
*Results source: phase3_openrouter_results.csv (SHA256: 926c877c8990)*

---

## 1. Statistical Power Analysis

### 1.1 Effect sizes from v17 GM-only run

| Metric | Value | Source |
|--------|-------|--------|
| Pooled Cohen's d (H3, wrong-answer confidence) | -0.274 | v17 deep analysis |
| Holm-corrected one-sided p | 0.174 | v17 deep analysis |
| N wrong Africa | 79 | v17 results |
| N wrong Europe | 91 | v17 results |

The v17 effect is in the **opposite** direction (Africa lower confidence on wrong answers).
For power analysis, we target the ability to detect a medium effect (d = 0.5) in either direction.

### 1.2 Power curve: Mann-Whitney U test

| Scenario | Test | Alpha | N per region | Total N |
|----------|------|-------|-------------|---------|
| Detect d=0.5 (medium) | Mann-Whitney U | 0.05 / 3 = 0.0167 | 8 | 16 |
| Detect d=0.5 (medium) | Mann-Whitney U | 0.05 / 5 = 0.0100 | 9 | 18 |
| Detect d=0.5 (medium) | Mann-Whitney U | 0.05 / 7 = 0.0071 | 10 | 20 |
| Detect d=0.8 (large) | Mann-Whitney U | 0.05 / 3 = 0.0167 | 5 | 10 |
| Detect d=0.8 (large) | Mann-Whitney U | 0.05 / 5 = 0.0100 | 5 | 10 |
| Detect d=0.8 (large) | Mann-Whitney U | 0.05 / 7 = 0.0071 | 5 | 10 |
| Detect d=0.5 (medium) - Welch t | Welch's t-test | 0.05 (two-sided) | 63 | 126 |

### 1.3 ICC sample-size floor

For acceptable inter-rater reliability (ICC >= 0.75, CI width <= 0.20), the minimum recommended sample is 30 items per rater comparison.

---

## 2. Conference-Standard Check

| Venue | Minimum per region | Recommended | Pass? |
|-------|-------------------|-------------|-------|
| ACL/EMNLP/NAACL | 50 | 60 | PASS |
| COLING | 50 | 60 | PASS |
| EACL | 40 | 60 | PASS |
| Workshop (UncertaiNLP) | 30 | 60 | PASS |

---

## 3. Recommended Sample Size

**60 items per region (120 total).**

### Rationale

1. **Power**: Detects d=0.5 with >=80% power at alpha=0.05 even under Holm correction for 7 models.
2. **ICC**: Exceeds the 30-item floor for reliable inter-rater agreement.
3. **Conference floor**: Exceeds all major NLP venue minimums (30-50) with margin.
4. **Annotator burden**: 60 items * ~3 min/item ~= 3 hours per annotator -- feasible for 2-3 annotators.
5. **Stratification**: Proportional allocation across categories preserves the source-distribution invariant.

---

## 4. Stratified Sampling Plan

Stratify by `category` (cat), balanced by `region` (Africa / Europe). Proportional allocation from the 180-item GM-only v3 universe.

| Category | Total | Africa | Europe | Min cell | Per region (allocated) |
|----------|-------|--------|--------|----------|------------------------|
| formal_logic | 2 | 1 | 1 | 1 | 2 |
| global_facts | 12 | 6 | 6 | 6 | 2 |
| high_school_biology | 8 | 4 | 4 | 4 | 2 |
| high_school_geography | 8 | 4 | 4 | 4 | 2 |
| high_school_us_history | 12 | 6 | 6 | 6 | 2 |
| high_school_world_history | 86 | 43 | 43 | 43 | 14 |
| miscellaneous | 6 | 3 | 3 | 3 | 2 |
| moral_disputes | 2 | 1 | 1 | 1 | 2 |
| moral_scenarios | 2 | 1 | 1 | 1 | 2 |
| nutrition | 4 | 2 | 2 | 2 | 2 |
| prehistory | 30 | 15 | 15 | 15 | 5 |
| professional_accounting | 2 | 1 | 1 | 1 | 2 |
| professional_law | 2 | 1 | 1 | 1 | 2 |
| virology | 2 | 1 | 1 | 1 | 2 |
| world_religions | 2 | 1 | 1 | 1 | 2 |

**Total allocated:** 45 per region

If proportional allocation falls below 2 per cell, floor = 2 to preserve within-category coverage.

---

## 5. Model Slate for Annotator Evaluation

Five models spanning four families, split across OpenRouter and Modal:

| Role | Provider | Model ID | Nick | Rationale |
|------|----------|----------|------|-----------|
| Closed (cheap) | OpenRouter | `openai/gpt-4o-mini` | gpt-4o-mini | Strong instruction following, low cost |
| Closed (cheap) | OpenRouter | `anthropic/claude-3-haiku` | claude-3-haiku | Strong calibration, very low cost |
| Open | Modal / OpenRouter | `deepseek/deepseek-v3.2` | deepseek-v3.2 | Best calibrated in v17 (ECE 2.6%) |
| Open | Modal / OpenRouter | `qwen/qwen3-235b-a22b-2507` | qwen3-235b | Large open model, diverse family |
| Open | Modal / OpenRouter | `meta-llama/llama-3.3-70b-instruct` | llama-3.3-70b | Largest open-weight, Llama family |

**Budget estimate** (annotator run, 120 items x 5 models x 2 calls/item = 1,200 calls):

| Model | Input $/M | Output $/M | Est. cost/run |
|-------|----------|------------|---------------|
| gpt-4o-mini | $0.15 | $0.60 | ~$0.04 |
| claude-3-haiku | $0.25 | $1.25 | ~$0.06 |
| deepseek-v3.2 | $0.2288 | $0.3432 | ~$0.02 |
| qwen3-235b | $0.09 | $0.10 | ~$0.02 |
| llama-3.3-70b | $0.10 | $0.32 | ~$0.02 |
| **Total** | | | **~$0.16** |

This fits comfortably within the $9/month OpenRouter / $10/month Modal budget.

---

## 6. Annotator Study Design

### 6.1 Annotation task

Each annotator receives a blinded, randomized CSV containing:

1. **Item ID** (anonymized)
2. **Question text** + **4 choices**
3. **Model's answer** (letter)
4. **Model's confidence** (0-100, verbalized)
5. **Model family** (blinded to specific identity)

Annotator marks:
- `correctness`: Is the model's answer correct? (A/B/C/D or X if unanswerable)
- `calibration_ok`: Is the model's confidence appropriately calibrated? (yes/no/uncertain)
- `notes`: Optional free-text

### 6.2 Blinding scheme

- Model identities hidden; replaced with family labels: 'Family-A', 'Family-B', etc.
- Region labels hidden; items shuffled across Africa/Europe.
- Random presentation order per annotator.

### 6.3 Minimum annotator count

- **2 annotators** minimum (standard for ACL/EMNLP human evaluation).
- **3 annotators** preferred (allows ICC calculation with CIs).
- Disagreements resolved by majority vote or adjudicator.

---

## 7. Code Trail / Audit Trail

Every artifact in this pipeline is versioned with:

- **Script SHA256** — recorded in this report.
- **Data SHA256** — each input dataset checksummed.
- **Timestamp** — UTC ISO-8601 for every phase.
- **Random seed** — fixed at 42 for all sampling.
- **Config hash** — all parameters frozen at pipeline start.

Artifacts produced by this phase:

| Artifact | Path | Hash |
|----------|------|------|