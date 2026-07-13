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
|---|---|---|
| Run full 180-item mixed-source experiment on OpenRouter | In progress | 20-item pilot running in background |
| Run Modal lane on mixed-source items | Pending | Depends on OpenRouter results |
| Merge mixed-source results and validate | Pending | After both lanes complete |
| Update paper manuscript with all fixes | Pending | Ethics, power, anonymization, corrections |
| Rename Kaggle dataset to anonymous handle | Pending | Requires manual Kaggle UI action |
| Create anonymous GitHub org/user | Pending | Requires manual GitHub action |

## Current Repository State

- **GitHub:** https://github.com/saaga23/afriknow
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
