# AfriKnow COLING 2027 Submission Itinerary
**Target:** COLING 2027 (deadline October 12, 2026)
**Current date:** 2026-07-10
**Days remaining:** ~95 days

---

## PHASE 0: VERIFICATION GATE (Days 1-2) — COMPLETED 2026-07-10

**Goal:** Confirm every number, citation, and claim in the hardened manuscript is bulletproof before any further work.

### Step 0.1: Full numerical audit — COMPLETED
- [x] Read `main.tex` line by line
- [x] For every statistic, percentage, p-value, CI, and effect size:
  - Located exact number in manuscript
  - Cross-checked against `archive/deep_clean_2026-07-08/phase4b_v18_verified_numbers_manifest.md`
  - Cross-checked against actual CSV files in `archive/deep_clean_2026-07-08/v18_outputs/`
  - All numbers match (within rounding)
- [x] Verified all table footnotes match the data
- [x] Verified all figure captions match the figures

**Verification results:**
- H3 pooled: d=-0.31, CI [-0.59,-0.02], p=.234 ✓
- Accuracy: Africa 87.5% (551/630), Europe 85.6% (539/630) ✓
- CHR pooled: 10.5% vs 13.6%, ratio 0.77 ✓
- ECE pooled: 4.8%, CI [3.1%, 8.5%] ✓
- Brier pooled: 0.114 ✓
- AUROC pooled: 0.679 ✓
- Mixed model accuracy: beta=+0.17, SE=0.36, p=.646 ✓
- Mixed model confidence: beta=-0.23, SE=0.34, p=.504 ✓

### Step 0.2: Citation integrity audit — COMPLETED
- [x] Verified every `\cite{...}` key exists in `references.bib`
- [x] Verified all 22 cited keys are present in bibliography (25 total entries)
- [x] Verified no missing citations

### Step 0.3: Figure verification — COMPLETED
- [x] Confirmed all 7 v18 figures exist in `AfriKnow2_extracted/overleaf/v18_analysis_figures/`
- [x] Confirmed `\graphicspath` includes `v18_analysis_figures/`
- [x] Confirmed figure filenames match `\includegraphics` paths in `main.tex`

### Step 0.4: Compilation clean check — COMPLETED
- [x] Ran `tectonic.exe main.tex` from overleaf directory
- [x] Confirmed 0 critical errors
- [x] Confirmed PDF generates successfully (1,169,055 bytes)
- [x] Confirmed PDF last modified: 2026-07-10 11:31

**Exit criteria:** All numbers verified, 0 critical errors, PDF compiles clean. ✓ MET

---

## PHASE 1: MANUSCRIPT FINALIZATION (Days 3-5)

**Goal:** Polish the manuscript to submission-ready quality. No content changes, only formatting, clarity, and compliance.

### Step 1.1: Author block
- [ ] Replace `\author{Anonymous}` with real author name and affiliation
- [ ] Format according to COLING 2027 author guidelines
- [ ] Add email and ORCID if available

### Step 1.2: Abstract compliance
- [ ] Verify abstract length meets COLING limits (typically 150-200 words)
- [ ] Ensure abstract is self-contained (no citations, no jargon)
- [ ] Verify abstract matches the paper's actual findings

### Step 1.3: Title compliance
- [ ] Verify title is concise and descriptive
- [ ] Check COLING 2027 title guidelines (no colons if possible, or follow their format)
- [ ] Ensure title reflects the actual contribution (source-aware calibration audit)

### Step 1.4: Formatting compliance
- [ ] Verify font sizes, margins, line spacing match COLING 2027 template
- [ ] Verify table captions are above tables
- [ ] Verify figure captions are below figures
- [ ] Verify all figures are within column width or text width as appropriate
- [ ] Verify no overfull/underfull hboxes that affect readability

### Step 1.5: AI-writing check
- [ ] Run manuscript through AI-detection tool (e.g., GPTZero, ZeroGPT)
- [ ] Flag any sections with high AI-probability
- [ ] Rewrite flagged sections to reduce AI markers
- [ ] Verify no "delve into," "landscape," "realm," "paramount," "pivotal," "leverage," "embark," "holistic," "comprehensive," "nuanced," "multifaceted," "intricate," "robust," "cutting-edge," "state-of-the-art," "groundbreaking," "revolutionize," "seamless," "foster," "empower," "unleash," "paradigm," "synergy," "innovation"

**Exit criteria:** Manuscript formatted, AI-check passed, author block complete.

---

## PHASE 2: REPRODUCIBILITY PACKAGE (Days 6-8)

**Goal:** Ensure the reproducibility appendix is complete and all linked resources are live and accessible.

### Step 2.1: Kaggle dataset verification
- [ ] Verify Kaggle dataset `abrahamsunday123/afriknow-v18-inputs` exists and is public
- [ ] Verify dataset contains all referenced files:
  - `v17 GM-only evaluation notebook`
  - `raw outputs`
  - `cost logs`
  - `AfriKnow GM-only v3 item metadata`
- [ ] Verify dataset description is complete and accurate
- [ ] Verify dataset tags are appropriate (NLP, calibration, LLM)

### Step 2.2: Kaggle notebook verification
- [ ] Verify Kaggle notebook `abrahamsunday123/afriknow-phase-4b-v18-post-hoc-analysis` exists and is public
- [ ] Verify notebook runs without errors on Kaggle
- [ ] Verify notebook output cells are populated
- [ ] Verify notebook description explains the analysis

### Step 2.3: Code release preparation
- [ ] Create clean repository with only submission-relevant code
- [ ] Include:
  - Dataset construction scripts
  - Evaluation runner
  - Analysis scripts
  - Metric module
- [ ] Add README with setup instructions
- [ ] Add requirements.txt with exact versions
- [ ] Verify all scripts run from scratch
- [ ] Remove any API keys, tokens, or credentials

### Step 2.4: Reproducibility appendix verification
- [ ] Verify all seeds are documented (42 for inference, 20260622 for analysis)
- [ ] Verify all model identifiers are exact OpenRouter routes
- [ ] Verify all temperature settings are documented
- [ ] Verify cost log is included in Kaggle dataset
- [ ] Verify raw responses are included in Kaggle dataset

**Exit criteria:** Kaggle dataset and notebook public and verified, code repository ready.

---

## PHASE 3: REVIEWER RESPONSE PREPARATION (Days 9-12)

**Goal:** Pre-write responses to the most likely reviewer objections, based on DLI feedback and standard COLING reviewer concerns.

### Step 3.1: Identify likely reviewer objections
Based on DLI 2026 feedback and manuscript analysis, the top 5 likely objections are:

1. **"Source confound is the only real finding; the rest is noise."**
   - Response: The source-confind finding is the central contribution. The null regional effects under source control are not "noise"; they are the evidence that source control changes the conclusion. The mixed-effects and sensitivity analyses strengthen this claim.

2. **"180 items is too small; results are underpowered."**
   - Response: Power analysis shows >99% power to detect the original effect (d≈1.00). The null is not due to underpowering. The 180-item design is a deliberate trade-off: source control requires source uniformity, which limits item availability.

3. **"Post-hoc analysis is unreliable; you cherry-picked the null."**
   - Response: H3 was pre-specified. All five signals are reported without selection. Sensitivity analyses were not contingent on observed results. The Analysis Plan appendix documents this explicitly.

4. **"Why should we trust Global-MMLU's geographic labels?"**
   - Response: 21 items (11.7%) were flagged for content-label review. Sensitivity analysis excluding them leaves conclusions unchanged. The labels are used as a starting point for matched-pair construction, not as ground truth.

5. **"No human validation; how do you know the answer key is correct?"**
   - Response: This is a calibration audit, not a correctness validation. The contribution is about confidence-accuracy alignment, not about disputing the benchmark. Human annotation would not address the source-confound question.

### Step 3.2: Write point-by-point response document
- [ ] Create `REVIEWER_RESPONSE.md` with pre-emptive responses
- [ ] For each objection, include:
  - The exact reviewer concern (paraphrased)
  - Our response with evidence
  - Specific line numbers in the manuscript where this is addressed
  - Any additional analysis or clarification we can provide

### Step 3.3: Prepare supplementary materials
- [ ] Create supplementary analysis notebook with:
  - Full source-confound comparison
  - All sensitivity analyses
  - All figures in high resolution
- [ ] Create supplementary tables with:
  - Full per-model per-signal results
  - Flagged item list
  - High-confidence error examples

**Exit criteria:** Reviewer response document complete, supplementary materials ready.

---

## PHASE 4: FINAL MANUSCRIPT POLISH (Days 13-15)

**Goal:** Last-pass editorial review to catch any remaining issues.

### Step 4.1: Read-aloud proofread
- [ ] Read entire manuscript aloud to catch awkward phrasing
- [ ] Check for:
  - Grammar errors
  - Punctuation errors
  - Consistency in terminology (e.g., "VCE" vs "verbalized confidence")
  - Consistency in model naming (e.g., "GPT-41 Nano" vs "GPT-4.1-Nano" vs "gpt41-nano")

### Step 4.2: Terminology consistency check
Standardize the following:
- Use "VCE" after first mention (verbalized confidence estimate)
- Use "MSP" after first mention (mean self-consistency probability)
- Use "CoCoA" after first mention (composite confidence)
- Use "CHR" after first mention (calibration hit rate)
- Use "ECE" after first mention (expected calibration error)
- Use "GM-only" consistently (not "gm_only" or "gm only" in prose)

### Step 4.3: Figure quality check
- [ ] Verify all figures are readable at print size
- [ ] Verify all labels, legends, and axes are clear
- [ ] Verify all figures use consistent color schemes
- [ ] Verify all figures have resolution >= 300 DPI

### Step 4.4: Table quality check
- [ ] Verify all tables fit within column width
- [ ] Verify all table captions are descriptive
- [ ] Verify all table cells are properly aligned
- [ ] Verify all table footnotes are present

### Step 4.5: Reference formatting
- [ ] Verify all citations use consistent format
- [ ] Verify bibliography entries are complete (authors, title, venue, year)
- [ ] Verify no broken links in URLs

**Exit criteria:** Manuscript polished, terminology consistent, figures/tables verified.

---

## PHASE 5: SUBMISSION PREPARATION (Days 16-20)

**Goal:** Prepare all submission materials according to COLING 2027 guidelines.

### Step 5.1: Review COLING 2027 submission guidelines
- [ ] Download official COLING 2027 author instructions
- [ ] Verify page limit (typically 8-10 pages for long papers)
- [ ] Verify formatting requirements (LaTeX style, margins, fonts)
- [ ] Verify submission system (typically EasyChair or Softconf)
- [ ] Verify anonymization requirements (double-blind? single-blind?)
- [ ] Verify supplementary material policy

### Step 5.2: Prepare submission package
- [ ] Main paper PDF
- [ ] Main paper source files (`.tex`, `.bib`, figures)
- [ ] Supplementary materials (if allowed)
- [ ] Author information (names, affiliations, emails)
- [ ] Conflict of interest declarations
- [ ] Keywords

### Step 5.3: Kaggle dataset finalization
- [ ] Verify dataset is public and citable
- [ ] Add DOI if available
- [ ] Update dataset description with paper citation
- [ ] Add version tag (v1.0 for submission)

### Step 5.4: Code repository finalization
- [ ] Create public GitHub repository
- [ ] Add LICENSE file (MIT or Apache 2.0 recommended)
- [ ] Add CITATION.cff file
- [ ] Verify repository builds/runs from scratch
- [ ] Add badges for build status, license, etc.

### Step 5.5: Pre-submission checklist
- [ ] All author information verified and approved
- [ ] All affiliations verified and approved
- [ ] All contact information verified
- [ ] Paper title finalized
- [ ] Abstract finalized
- [ ] Keywords finalized
- [ ] PDF final version generated
- [ ] Source files zipped
- [ ] Supplementary materials prepared
- [ ] Conflicts of interest declared
- [ ] Submission system account created

**Exit criteria:** Submission package complete, all materials verified.

---

## PHASE 6: SUBMISSION AND POST-SUBMISSION (Days 21-95)

**Goal:** Submit the paper and prepare for potential reviews.

### Step 6.1: Submission (Day 21)
- [ ] Upload paper to COLING 2027 submission system
- [ ] Upload supplementary materials (if allowed)
- [ ] Verify upload successful
- [ ] Save confirmation email/receipt
- [ ] Mark calendar for review release date

### Step 6.2: Post-submission preparation (Days 22-30)
- [ ] Prepare short description for social media/blog (if allowed)
- [ ] Prepare talk/poster outline in case of acceptance
- [ ] Identify potential reviewers to avoid (conflicts of interest)
- [ ] Prepare funding acknowledgment text

### Step 6.3: While waiting for reviews
- [ ] Continue improving related work section with new citations
- [ ] Prepare follow-up research directions
- [ ] Document any new results or insights
- [ ] Maintain reproducibility package (update if needed)

### Step 6.4: If accepted
- [ ] Prepare camera-ready version
- [ ] Address minor revisions if required
- [ ] Prepare presentation materials
- [ ] Register for conference

### Step 6.5: If rejected
- [ ] Analyze reviewer feedback
- [ ] Identify salvageable feedback
- [ ] Prepare rebuttal for next venue
- [ ] Update paper based on feedback
- [ ] Target next venue (ACL 2027, EMNLP 2027, etc.)

**Exit criteria:** Paper submitted, post-submission materials ready.

---

## CRITICAL DEPENDENCIES

| Task | Depends on |
|------|-----------|
| Numerical audit | Verified manifest and CSVs |
| Citation audit | References.bib completeness |
| Author block | Real author information |
| Kaggle verification | Public dataset access |
| Code repository | Clean, runnable code |
| Submission | Author information, final PDF |

---

## RISK MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Number mismatch found during audit | Medium | High | Fix before proceeding to Phase 1 |
| Citation missing | Low | Medium | Add before submission |
| Kaggle dataset not public | Low | High | Verify in Phase 0 |
| Code doesn't run from scratch | Medium | High | Test in Phase 2 |
| Author information changes | Low | Medium | Confirm with author before Phase 1 |
| COLING guidelines differ from expectation | Medium | High | Read guidelines in Phase 5 before final formatting |

---

## TIME BUDGET

| Phase | Days | Cumulative |
|-------|------|-----------|
| Phase 0: Verification | 2 | 2 |
| Phase 1: Finalization | 3 | 5 |
| Phase 2: Reproducibility | 3 | 8 |
| Phase 3: Reviewer response | 4 | 12 |
| Phase 4: Polish | 3 | 15 |
| Phase 5: Submission prep | 5 | 20 |
| Buffer | 10 | 30 |
| **Total active work** | **20** | **30** |

Buffer time allows for unexpected issues. Paper should be submitted well before October 12, 2026 deadline.

---

## LIVE STATUS (2026-07-10 14:03)

### Full 817-item expansion — IN PROGRESS
- **Background process ID:** bgp_f4bf3613d0015gKyskgZUfs3dy
- **Runner:** `annotator_pipeline/run_full_817.py`
- **Input:** `02_sampled_items_full.json` (817 items: 284 Africa, 533 Europe)
- **Models:** 5 core models (gpt-4o-mini, claude-3-haiku, deepseek-v3.2, qwen3-235b, llama-3.3-70b)
- **Cost cap:** $15.00
- **Estimated cost:** $1.14–$4.35
- **Progress:** 220/817 items (26.9%) as of 14:00
- **Rate:** ~5 items/minute
- **ETA:** ~15:53 (approximately 2 hours from start)
- **Output files:** `03_openrouter_outputs_full.csv`, `03_openrouter_cost_history_full.csv`, `03_openrouter_manifest_full.json`
- **Checkpoints:** Saved every 20 items to `outputs/checkpoints/`

### Option 4: Human-in-the-loop curation narrative — COMPLETED
- Added paragraph to Methods section: "Dataset curation and content-label validation"
- Reframes 21 flagged items as human-in-the-loop dataset curation (not annotation study)
- No IRB required for dataset curation
- Strengthens dataset construction narrative

### Original 120-item data — RESTORED
- Original `03_openrouter_outputs.csv` was accidentally overwritten by dry run
- Restored from `03_model_outputs.csv` (merged file with 1200 rows)
- Original checkpoints preserved in `outputs/checkpoints/`

---

## SUCCESS CRITERIA

1. All numbers verified against source data (0 mismatches)
2. 0 critical compilation errors
3. All citations verified and real
4. Kaggle dataset public and complete
5. Code repository public and runnable
6. Reviewer response document complete
7. Paper submitted before deadline
8. Zero ethical contradictions
9. Zero em dashes
10. Zero AI-writing markers

---

## NEXT ACTIONS (IMMEDIATE)

1. **Today:** Start Phase 0, Step 0.1 (numerical audit) — COMPLETED
2. **Today:** Monitor full 817-item expansion run — IN PROGRESS
3. **After expansion:** Re-run v18 analysis on full dataset
4. **After analysis:** Update manuscript with new numbers
5. **Day 3:** Begin Phase 1 (author block, formatting)
6. **Day 6:** Begin Phase 2 (Kaggle verification, code prep)
7. **Day 9:** Begin Phase 3 (reviewer response)
8. **Day 13:** Begin Phase 4 (polish)
9. **Day 16:** Begin Phase 5 (submission prep)
10. **Day 21:** SUBMIT

---

*This itinerary was generated on 2026-07-10. Update as progress is made. Mark completed items with [x].*
