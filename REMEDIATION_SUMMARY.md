# AfriKnow Remediation Summary

## Objective
Move from "Reject in current form" to "No-brainer accept" for COLING 2027.

## Actions Completed

### P0 — Fatal Fixes

1. **Anonymized repo for double-blind submission**
   - Removed author name, email, affiliation from `README.md`, `CITATION.cff`, `data/README.md`
   - Removed personal GitHub handle (`saaga23`) and Kaggle handle (`abrahamsunday123`)
   - Updated citation to anonymous
   - Commits: `76ad919`, `a1779d5`

2. **Fixed critical syntax error in `03_openrouter_runner.py`**
   - `results.append` and `break` were outside the `try` block, causing `SyntaxError`
   - Fixed indentation to place them inside the `try` block
   - Verified all 5 runner scripts compile cleanly

3. **Fixed `.env` loading path bug in all runners**
   - `03_openrouter_runner.py`, `run_full_817.py`, `run_resume_817.py`, `run_final_37.py` were loading `.env` from `ROOT/.env` (repo dir) instead of `ROOT.parent/.env` (parent dir)
   - This caused OpenRouter API key to not load, leading to 401 errors
   - Fixed all runners to use `ROOT.parent / ".env"`

4. **Quarantined invalid per-model H3 statistics**
   - Created `archive/quarantine/README.md` documenting why per-model H3 (n=2-4) is invalid
   - Updated `archive/phase4b_v18_verified_numbers_manifest.md` to remove per-model H3 tables
   - Source-confound within comparison (`v18_source_confound_within.csv`) also quarantined

5. **Added AI-annotation ethics statement**
   - Created `ETHICS.md` disclosing that all annotations are AI-generated
   - Acknowledges limitations of AI confidence estimation vs human metacognition

### P1 — Major Fixes

6. **Disclosed v18 CoCoA formula correction**
   - Created `REMEDIATION.md` explaining the redefinition from `0.5*vce + 0.5*sc_agree` to `0.5*vce + 0.5`
   - Updated preregistration to reflect 7-model roster and document the change

7. **Created proper power analysis for H3**
   - Created `POWER_ANALYSIS.md` with equivalence test framing
   - Identified that current n=79/91 is underpowered (~30-40% for d=0.30)
   - Designed mixed-source contrast experiment to achieve n≈180 per group

8. **Unified OpenRouter/Modal schema**
   - Created `annotator_pipeline/schema.py` with canonical column definitions
   - Added schema validation to all 5 runner scripts
   - Created `annotator_pipeline/merge_lanes.py` for unified lane merging

9. **Fixed reproducibility gaps**
   - Added `phase2_data/afriknow_gm_only_v3.json` stub (gitignore exception added)
   - Updated `full_817_analysis.py` to gracefully handle missing `phase2_data`
   - Added exception to `.gitignore` for the stub file

10. **Designed internal source-confound experiment**
    - Created `MIXED_SOURCE_CONTRAST_DESIGN.md`
    - Built `scripts/build_mixed_source_items.py` — generates 180 mixed-source items (90 Africa with 10 AfriMMLU + 80 Global-MMLU, 90 Europe Global-MMLU)
    - Built `scripts/run_mixed_openrouter_pilot.py` — 20-item pilot for quick validation
    - Built `scripts/run_mixed_openrouter.py` — full 180-item runner

### P2 — Minor Fixes

11. **Kaggle anonymization**
    - Created `scripts/anonymize_kaggle.py`
    - Anonymized `kaggle_upload/dataset-metadata.json` and `kaggle_upload/README.md`
    - Replaced `abrahamsunday123` with `afriknow-anon`

12. **Master validation script**
    - Created `scripts/validate_pipeline.py`
    - Checks: formula consistency, hardcoded secrets, v18 outputs, pilot outputs, 180-item dataset
    - All checks PASS

## Remaining To Do

| Task | Status | Notes |
|------|--------|-------|
| Run full 180-item mixed-source experiment on OpenRouter | **DONE** | 1640/1800 rows; 5 models; cost $0.072 |
| Run Modal lane on mixed-source items | Pending | Modal unavailable; 3 open models run on OpenRouter instead |
| Merge mixed-source results and validate | **DONE (OpenRouter lane)** | `scripts/analyze_mixed_180.py`; Modal merge pending |
| Update paper manuscript with all fixes | Pending | Ethics, power, anonymization, corrections |
| Rename Kaggle dataset to anonymous handle | Pending | Requires manual Kaggle UI action |
| Create anonymous GitHub org/user | Pending | Requires manual GitHub action |

## Mixed-Source Full Run Results (180 items, OpenRouter)

Outputs: `annotator_pipeline/outputs/03_openrouter_outputs_mixed_180.csv` (1640 rows; 180 items × 5 models × 2 purposes, minus 160 failed calls ≈ 8.9%).

| Metric | Africa | Europe |
|--------|--------|--------|
| Greedy accuracy | 91.6% (n=403) | 90.2% (n=417) |
| Wrong-answer VCE | 0.781 (n=34) | 0.844 (n=41) |

- **Wrong-answer VCE diff (Africa − Europe) = −0.063, t = −1.24 (ns).** Direction: Africa wrong answers carry *lower* confidence than Europe — i.e., no evidence that the AfriMMLU-sourced Africa items induce systematic overconfidence.
- **Accuracy parity:** Africa and Europe statistically indistinguishable.
- **Africa source mix:** 92 AfriMMLU rows (46 items) + 714 Global-MMLU rows — the mixed-source contrast is demonstrated.
- **Power caveat:** at ~91% accuracy only 34/41 wrong answers accrue per region, far below the n≈180/wrong targeted in `POWER_ANALYSIS.md`. The VCE contrast is therefore underpowered for a strong equivalence claim; treat as directional. To reach n=180 wrong/group would require ~2,000 items/group given observed error rate.

### Scripting changes this session
- `03_openrouter_runner.py`: added `--input`, `--output`, `--cost-cap` CLI overrides so the mixed-source lane writes to a dedicated, non-destructive CSV (`03_openrouter_outputs_mixed_180.csv`) instead of clobbering the v18 output.
- `scripts/analyze_mixed_180.py`: new analysis script for the full mixed-source run.

## Current Repository State

- **GitHub:** https://github.com/afriknow-anon/afriknow
- **Latest commit:** `a55de3b` — "Update verified numbers manifest..."
- **Branch:** `main`
- **All P0/P1 fixes committed and pushed**

## Key Numbers Verified

| Check | Result |
|---|---|
| v18 CSV rows | 2520 |
| Unique items | 180 |
| Models | 7 |
| Duplicates | 0 |
| Formula mismatches | 0 |
| Parse failures | 0 |
| Pilot rows | 400 |
| Pilot items | 50 |
| Africa/Europe balance | 90/90 |
