# AfriKnow v18 Formula Correction

## What Changed

The original v18 archive computed CoCoA as:
```
CoCoA = 0.5 * VCE + 0.5 * sc_agree
```

Because self-consistency (SC) sampling was **not completed** in the final run, the repo standardizes CoCoA to:
```
CoCoA_fixed = 0.5 * VCE + 0.5
```

## Files Affected

- `annotator_pipeline/outputs/03_openrouter_outputs_v18_correct.csv` — recomputed with `cocoa_fixed = 0.5 * vce + 0.5`
- `annotator_pipeline/outputs/03_openrouter_manifest_v18.json` — documents the formula
- All runner scripts (`run_pilot_50.py`, `03_openrouter_runner.py`, `run_full_817.py`, `run_resume_817.py`, `run_final_37.py`) — use the standardized formula

## Transparency Statement

> "The original v18 archive computed CoCoA as 0.5·VCE + 0.5·SC_agree. Because self-consistency sampling was not completed in the final run, we redefined CoCoA as 0.5·VCE + 0.5 for all reported analyses. All results are reproducible from the repository CSV using this formula."
