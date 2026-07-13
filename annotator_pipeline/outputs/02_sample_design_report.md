# AfriKnow Annotator Pipeline — Sample Design Report

*Generated: 2026-07-06 15:21:53 UTC*
*Script: C:\Users\USER\Downloads\Revamp\annotator_pipeline\02_sample_design.py*

---

## 1. Parameters

- **N per region:** 60
- **Total items:** 120
- **Random seed:** 42
- **Excluded flagged:** 21 content-label-mismatch IDs
- **Source:** GM-only v3 (180 items, 90 Africa / 90 Europe)

---

## 2. Sampling Procedure

1. Remove 22 flagged content-label-mismatch IDs from the candidate pool.
2. Stratify by `category` x `region`.
3. Proportional allocation: each category receives at least 2 items per region, scaled by its share of the 180-item universe.
4. Random sample without replacement within each stratum (seed=42).
5. If allocation falls short of 60/region, top-up from the largest remaining pools.
6. Assign anonymized IDs: `ANN-AF-001`...`ANN-AF-060`, `ANN-EU-001`...`ANN-EU-060`.

---

## 3. Final Distribution

### 3.1 By region

| Region | Count |
|--------|-------|
| Africa | 60 |
| Europe | 60 |
| **Total** | **120** |

### 3.2 By category

| Category | Africa | Europe | Total |
|----------|--------|--------|-------|
| formal_logic | 1 | 1 | 2 |
| global_facts | 5 | 5 | 10 |
| high_school_biology | 3 | 3 | 6 |
| high_school_geography | 3 | 3 | 6 |
| high_school_world_history | 28 | 27 | 55 |
| miscellaneous | 2 | 2 | 4 |
| moral_disputes | 1 | 1 | 2 |
| moral_scenarios | 1 | 1 | 2 |
| nutrition | 2 | 2 | 4 |
| prehistory | 11 | 11 | 22 |
| professional_accounting | 1 | 1 | 2 |
| professional_law | 0 | 1 | 1 |
| virology | 1 | 1 | 2 |
| world_religions | 1 | 1 | 2 |

---

## 4. Quality Checks

| Check | Result |
|-------|--------|
| Total items = 120 | PASS |
| Africa = 60 | PASS |
| Europe = 60 | PASS |
| No flagged IDs | PASS |
| All answers A-D | PASS |
| Seed reproducible | PASS |

---

## 5. Provenance

- **Source SHA256:** `2193db46e849`
- **Output SHA256:** `6ca72c68d71f`
- **Script SHA256:** `6ae2a4f5e50a`
- **Timestamp:** 2026-07-06T15:21:53.135486+00:00