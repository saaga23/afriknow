# AfriKnow v17 Manuscript — Compilation Report

**Date:** 2026-06-21
**Compiler:** Tectonic 0.16.9 (XeLaTeX-based, downloaded to `Revamp/tools/`)
**Source:** `AfriKnow2_extracted/overleaf/main.tex`
**Output:** `AfriKnow2_extracted/overleaf/main.pdf`

---

## Compilation result

- **Status:** SUCCESS
- **Pages:** 9
- **File size:** 647.6 KiB
- **Errors:** 0
- **Overfull boxes:** 0 (after table layout fixes)
- **Underfull boxes:** minor, in literature-review table (acceptable for dense table)

---

## Fixes applied to make it compile

| Issue | Fix |
|---|---|
| `\pdfinfo` undefined under XeLaTeX | Removed the optional `/TemplateVersion` metadata block |
| `\citet` undefined in IJCAI26 style | Replaced all 11 `\citet{...}` with `\citeauthor{...}~\shortcite{...}` |
| Literature-review table 113pt overfull | Reduced to `\scriptsize`, narrower `p{}` columns, shortened cell text |
| Run-quality table 35pt overfull | Abbreviated headers, reduced tabcolsep |
| CHR table 113pt overfull | Abbreviated headers (`CHR Af`, `$N$ Af`, etc.), reduced tabcolsep |
| H3 table 27pt overfull | Abbreviated headers (`$d$`, `$\delta$`, `$N$ Af/Eu`), reduced tabcolsep |
| Mixed-effects table 53pt overfull | Moved model formulas to caption, used `\scriptsize`, abbreviated model name |
| ECE/Brier table 29pt overfull | Abbreviated headers (`ECE Af/Eu`, `Brier`), reduced tabcolsep |

---

## Verification after compilation

| Check | Result |
|---|---|
| AI-detection agent | PASS (no filler words, no first person) |
| Fact-checking agent | PASS (all numbers match verified manifest) |
| Citation/plagiarism agent | PASS (25/25 bib keys, all real 2022–2026) |
| Figures referenced | All 5 PNGs present and referenced |

---

## Sample output

First-page text sample saved to: `AfriKnow2_extracted/overleaf/main_sample.txt`

PDF location: `AfriKnow2_extracted/overleaf/main.pdf`

---

## Tooling note

Tectonic was chosen because it downloads required LaTeX packages on demand and does not require a full TeX Live/MiKTeX install. The binary is kept at `Revamp/tools/tectonic.exe` for future recompilations.
