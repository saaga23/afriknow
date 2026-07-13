# AfriKnow v17 Manuscript — Multi-Agent Pipeline Handoff

**Date:** 2026-06-21
**Status:** All phases complete. Draft ready for submission polish.

---

## What was delivered

| Phase | Agent | Status | Key output |
|-------|-------|--------|------------|
| 0 — Conference targeting | Explore agent | Done | COLING 2027 recommended primary target (deadline Oct 12, 2026); EACL 2027 fast-track option (Aug 3, 2026); UncertaiNLP @ EMNLP 2026 workshop safety net |
| 1 — Fact-checking | Coder agent | Done | `phase4b_v17_verified_numbers_manifest.md` — 105 claims checked, 105 PASS |
| 2 — Literature review | Explore agent | Done | Strict 5-column table with 23 real 2022–2026 papers |
| 4 — Drafting | Human-in-the-loop rewrite | Done | `AfriKnow2_extracted/overleaf/main.tex` rewritten around source-aware calibration audit |
| 3 — AI detection triad | 3 independent agents | All PASS | No AI filler, no first person, passive voice, concise title, roadmap present |
| 3 — Plagiarism/citation | Explore agent | PASS | All 25 bib keys cited, all 23 table papers real and correctly authored |
| 3 — Final fact-check | Coder agent | PASS | All numbers match verified manifest; figures present |

---

## Manuscript location

- **LaTeX source:** `AfriKnow2_extracted/overleaf/main.tex`
- **Bibliography:** `AfriKnow2_extracted/overleaf/references.bib`
- **Figures:** `AfriKnow2_extracted/overleaf/v17_analysis_figures/`
- **Backups:** `main.tex.old`, `references.bib.old`

---

## Conference recommendation

**Primary target:** COLING 2027 — submit to ARR October 2026 cycle, deadline **October 12, 2026**.
- Strong thematic fit (bias/fairness, evaluation, multilingualism, interpretability).
- ~31% historical acceptance rate — best balance of prestige and realistic acceptance.
- Gives ~4 months for final polish.

**Aggressive co-target:** EACL 2027 — ARR deadline **August 3, 2026**. Only viable if a complete review-ready draft exists within ~6 weeks.

**Workshop safety net:** UncertaiNLP @ EMNLP 2026 — deadline **August 7, 2026**.

**Late fallback:** ACL 2027 — predicted January 2027 deadline.

---

## Narrative pivot

The old 350-question, 4-model Africa-overconfidence headline (Cohen's $d = 1.00$) has been replaced by the v17 source-aware calibration audit framing:

- 7 models × 180 Global-MMLU items (90 Africa / 90 Europe).
- No accuracy gap: Africa 87.5% vs. Europe 85.6%, $\chi^2 = 0.82$, $p = .364$.
- No Africa overconfidence on wrong answers: pooled Cohen's $d = -0.27$, Holm-corrected two-sided $p = .174$.
- Calibration Hit Rate favors Africa: 10.6% vs. 13.5% wrong among high-confidence predictions, ratio 0.79.
- Mixed-effects headline model: Europe marginal effect $\beta = +0.0094$, $z = 1.73$, $p = .083$.
- Model-specific calibration patterns via Brier/ECE reported.

---

## Verified numbers summary

All numbers in the manuscript were cross-checked against `phase4b_v17_verified_numbers_manifest.md`:
- 1,260 observations, 180 unique items, 0 failures, $1.3408 cost.
- H1, H2/CHR, H3, ECE/Brier, and mixed-effects values all match.
- Three Cohen's $d$ values in Table 3 were corrected during review.

---

## Style compliance

- Passive voice throughout; no "I", "We", "our", "us", "my".
- No AI filler words (delve, tapestry, showcase, robust, etc.).
- Technical terms glossed on first use: distractor, greedy answer, ICC, RLHF.
- Concise 10-word title.
- Introduction ends with explicit section roadmap.

---

## Literature review

- 23 papers, strict 5-column table, all 2022–2026.
- All citations verified as real published works.
- Bibliography corrected for author-list accuracy on 6 entries.

---

## Known limitations stated in paper

1. Medium-difficulty items only.
2. Single source (Global-MMLU).
3. Seven-model sample, English-centric.
4. Post-hoc hypothesis refinement.
5. Equal-weight VCE/MSP composite.
6. Africa and Europe treated as monolithic regions.

---

## Next steps for the user

1. Read `AfriKnow2_extracted/overleaf/main.tex` end-to-end.
2. Compile with pdflatex/bibtex (not available in this environment) and fix any remaining LaTeX issues.
3. Add author names and affiliations.
4. Decide on COLING 2027 vs. EACL 2027 target by **June 23, 2026**.
5. Prepare optional UncertaiNLP workshop submission as safety net.
6. Draft reviewer-response memo explaining the source-control pivot (optional).

---

## Agent reports

- `phase4b_v17_verified_numbers_manifest.md` (Phase 1)
- `phase4b_v17_manuscript_fact_check_report.md` (Phase 3)
- This handoff file
