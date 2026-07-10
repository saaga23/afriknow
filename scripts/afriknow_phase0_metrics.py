"""
afriknow_phase0_metrics.py
==========================
Canonical metric implementations for the AfriKnow revision.

This module locks the definitions agreed in Phase 0:
  - ECE: equal-width bins (primary); equal-mass bins (sensitivity).
  - sc_agree (paper MSP): self-consistency agreement fraction.
  - logprob_conf: normalized log-probability of greedy prediction (auxiliary).
  - VCE: robustly parsed from integer 0-100 or decimal 0-1.
  - TSCE: normalized entropy of SC samples, retaining invalid (X) predictions.
  - CoCoA: alpha * vce + (1 - alpha) * sc_agree.
  - H3 battery: Welch's t, Mann-Whitney U, Cohen's d, Cliff's delta,
    mixed-effects model.

All functions are deterministic and do not require API access.
"""

from __future__ import annotations

import math
import re
import warnings
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Optional mixed-effects model dependency
try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    HAS_STATSMODELS = True
except ImportError:  # pragma: no cover
    HAS_STATSMODELS = False

LABS = ["A", "B", "C", "D"]
N_OPTIONS = len(LABS)
DEFAULT_ECE_BINS = 10


# ---------------------------------------------------------------------------
# ECE
# ---------------------------------------------------------------------------
def compute_ece_equal_width(
    conf: np.ndarray,
    corr: np.ndarray,
    n_bins: int = DEFAULT_ECE_BINS,
) -> Tuple[float, List[Dict]]:
    """
    Expected Calibration Error with equal-width bins on [0, 1].

    This is the primary ECE definition used in the paper.
    Empty bins are skipped and do not contribute to the weighted sum.
    """
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    n = len(c)
    if n == 0:
        return 0.0, []

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Tiny expansion to ensure 0 and 1 fall inside the first/last bin
    edges[0] -= 1e-9
    edges[-1] += 1e-9

    ece = 0.0
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (c > lo) & (c <= hi)
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        acc_b = float(r[mask].mean())
        conf_b = float(c[mask].mean())
        ece += (n_b / n) * abs(acc_b - conf_b)
        bins.append(
            {
                "lo": float(lo),
                "hi": float(hi),
                "n": n_b,
                "acc": acc_b,
                "conf": conf_b,
            }
        )
    return float(ece), bins


def compute_ece_equal_mass(
    conf: np.ndarray,
    corr: np.ndarray,
    n_bins: int = DEFAULT_ECE_BINS,
) -> Tuple[float, List[Dict]]:
    """
    Expected Calibration Error with equal-mass (quantile) bins.

    This is the sensitivity variant that was actually implemented in v11.
    It is retained so reviewers can verify robustness to binning strategy.
    """
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    n = len(c)
    if n == 0:
        return 0.0, []

    if n < n_bins:
        n_bins = max(2, n // 2)

    edges = np.quantile(c, np.linspace(0.0, 1.0, n_bins + 1))
    edges[0] -= 1e-9
    edges[-1] += 1e-9

    ece = 0.0
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (c > lo) & (c <= hi)
        n_b = int(mask.sum())
        if n_b == 0:
            continue
        acc_b = float(r[mask].mean())
        conf_b = float(c[mask].mean())
        ece += (n_b / n) * abs(acc_b - conf_b)
        bins.append(
            {
                "lo": float(lo),
                "hi": float(hi),
                "n": n_b,
                "acc": acc_b,
                "conf": conf_b,
            }
        )
    return float(ece), bins


# ---------------------------------------------------------------------------
# Auxiliary metrics
# ---------------------------------------------------------------------------
def compute_brier(conf: np.ndarray, corr: np.ndarray) -> float:
    """Mean squared error between confidence and correctness."""
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    if len(c) == 0:
        return 0.0
    return float(np.mean((c - r) ** 2))


def compute_chr(
    conf: np.ndarray, corr: np.ndarray, tau: float = 0.7
) -> Tuple[float, int]:
    """Calibration Hit Rate at threshold tau: fraction wrong among high-confidence."""
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    high = c >= tau
    n_high = int(high.sum())
    if n_high == 0:
        return 0.0, 0
    return float((1 - r[high]).mean()), n_high


def compute_auroc(conf: np.ndarray, corr: np.ndarray) -> float:
    """AUROC where higher confidence predicts wrong answer."""
    try:
        from sklearn.metrics import roc_auc_score
    except ImportError:  # pragma: no cover
        warnings.warn("sklearn not installed; returning 0.5 for AUROC")
        return 0.5

    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    valid = np.isfinite(c) & np.isfinite(r)
    c, r = c[valid], r[valid]
    if len(r) < 2 or r.sum() == 0 or r.sum() == len(r):
        return 0.5
    # Predict wrong answer (1-r) from high confidence (1-c)
    return float(roc_auc_score(1 - r, 1 - c))


def compute_kgi(ece_test: float, ece_baseline: float) -> Tuple[float, float]:
    """Knowledge Gap Index: ratio and absolute difference of ECEs."""
    ratio = float(ece_test) / max(float(ece_baseline), 1e-8)
    absdif = float(ece_test) - float(ece_baseline)
    return ratio, absdif


def compute_conf_gap(conf: np.ndarray, corr: np.ndarray) -> Tuple[float, float, float]:
    """Mean confidence gap: correct - wrong."""
    c = np.asarray(conf, dtype=float)
    r = np.asarray(corr, dtype=float)
    mc = float(c[r == 1].mean()) if r.sum() > 0 else 0.0
    mw = float(c[r == 0].mean()) if (1 - r).sum() > 0 else 0.0
    return mc - mw, mc, mw


# ---------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------
def parse_letter(text) -> str:
    """Parse a multiple-choice answer letter from model text."""
    if text is None:
        return "X"
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL)

    answer_patterns = [
        r"the best answer is\s+([A-D])\b",
        r"the correct answer is\s+([A-D])\b",
        r"final answer\s*[:=]?\s*([A-D])\b",
        r"answer\s*[:=]\s*([A-D])\b",
        r"answer is\s+([A-D])\b",
    ]
    for pat in answer_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            return matches[-1].upper()

    m = re.search(r"\b([A-D])\b", text)
    if m:
        return m.group(1).upper()
    if text.strip() and text.strip()[0].upper() in "ABCD":
        return text.strip()[0].upper()
    return "X"


# ---------------------------------------------------------------------------
# Confidence signals
# ---------------------------------------------------------------------------
def compute_sc_agree(sc_preds: List[str], greedy_pred: str) -> float:
    """
    Self-consistency agreement (paper MSP).

    Fraction of self-consistency predictions that match the greedy prediction.
    Invalid predictions ('X') are counted as non-matching.
    """
    if not sc_preds:
        return 1.0 / N_OPTIONS  # chance level
    matches = sum(1 for p in sc_preds if p == greedy_pred and p in LABS)
    return matches / len(sc_preds)


def logprobs_to_probs(lp_content) -> Tuple[Dict[str, float], bool]:
    """
    Convert API top_logprobs structure to normalized probabilities.

    This is retained as an auxiliary helper; it is NOT used in canonical CoCoA.
    """
    scores = {lab: -999.0 for lab in LABS}
    if not lp_content:
        return {lab: 1.0 / N_OPTIONS for lab in LABS}, False
    try:
        top5 = lp_content[0].top_logprobs
    except (IndexError, AttributeError):
        return {lab: 1.0 / N_OPTIONS for lab in LABS}, False

    for item in top5:
        tok = str(getattr(item, "token", "")).strip().upper().rstrip(".):")[:1]
        if tok in LABS and item.logprob > scores[tok]:
            scores[tok] = item.logprob

    mx = max(scores.values())
    raw = {lab: math.exp(lp - mx) for lab, lp in scores.items()}
    tot = sum(raw.values())
    if tot <= 0:
        return {lab: 1.0 / N_OPTIONS for lab in LABS}, False
    return {lab: v / tot for lab, v in raw.items()}, True


def compute_logprob_conf(lp_content, pred: str) -> float:
    """Normalized log-probability of the greedy prediction. Auxiliary only."""
    probs, ok = logprobs_to_probs(lp_content)
    if not ok:
        return 1.0 / N_OPTIONS
    return probs.get(pred, 1.0 / N_OPTIONS)


def extract_conf(text: str) -> float:
    """
    Parse a verbalized confidence value to [0, 1].

    Handles both integer percentages ("85", "85%") and decimal proportions
    ("0.85"). The original v11 code divided any number by 100, which corrupted
    decimal responses into values near zero.

    Robustness: reasoning models often append the confidence at the very end
    (e.g. "Confidence (0-100): 80") after a chain of thought. We therefore
    prefer numbers near a confidence marker, then the last number in the text,
    rather than the first number (which may be a year/statistic).

    Years (values >= 1000) are rejected unless they are explicitly labelled as
    confidence, preventing question-year leakage into the confidence estimate.
    """
    if text is None:
        return 0.5
    clean = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL).strip()
    if not clean:
        return 0.5

    explicit_marker = False
    # Prefer a number explicitly labelled as confidence (case-insensitive).
    m = re.search(
        r"confidence\s*[:\(]?\s*0?[-–]\s*100\)?\s*[:=]?\s*[:=]?\s*(\d+\.?\d*)",
        clean, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r"confidence\s*[:=]?\s*(\d+\.?\d*)", clean, re.IGNORECASE
        )
    if not m:
        # Handle expressions like "90/100" or "Confidence: 90/100".
        m = re.search(
            r"(?:confidence\s*[:=]?\s*)?(\d+\.?\d*)\s*/\s*100\b",
            clean, re.IGNORECASE
        )
    if m:
        raw_str = m.group(1)
        explicit_marker = True
    else:
        # Fall back to the last number in the response (closest to the final answer).
        nums = re.findall(r"\d+\.?\d*", clean)
        if not nums:
            return 0.5
        raw_str = nums[-1]

    raw = float(raw_str)
    # Reject values that cannot be valid percentages or proportions (e.g. years
    # like 2016, or explicit-but-nonsensical values like "Confidence: 150").
    if raw > 100:
        return 0.5

    # Heuristic: if the matched string looks like a decimal proportion, use it
    # directly; otherwise divide by 100.
    if raw <= 1.0 and ("." in raw_str or raw == 0):
        return float(min(max(raw, 0.0), 1.0))
    return float(min(max(raw, 0.0), 100.0) / 100.0)


def compute_tsce(sc_preds: List[str]) -> float:
    """
    Temperature-Scaled Consistency Entropy.

    Normalized empirical entropy of self-consistency samples. Invalid
    predictions ('X') are retained as a fifth category to avoid downward bias
    from non-random parse failures. No additional temperature scaling is
    applied beyond the sampling temperature of 0.8.
    """
    valid = [p for p in sc_preds if p]  # keep 'X' as well
    if not valid:
        return 0.5
    counts = Counter(valid)
    n = len(valid)
    probs = np.array([counts.get(lab, 0) / n for lab in LABS + ["X"]])
    probs = probs[probs > 0]
    if len(probs) == 0:
        return 0.5
    H = -np.sum(probs * np.log(probs))
    # Normalize by the maximum possible entropy. X is retained as a fifth
    # category, so the support size is 5, not 4.
    return float(H / math.log(N_OPTIONS + 1))


# ---------------------------------------------------------------------------
# CoCoA
# ---------------------------------------------------------------------------
def compute_cocoa(vce: float, sc_agree: float, alpha: float = 0.5) -> float:
    """
    Canonical Composite Confidence Aggregator.

    Matches the paper equation: alpha * VCE + (1 - alpha) * MSP,
    where MSP is now renamed sc_agree.
    """
    return float(alpha * vce + (1.0 - alpha) * sc_agree)


def compute_cocoa_tsce(msp_used: float, tsce: float, alpha: float = 0.5) -> float:
    """
    Legacy TSCE variant retained for sensitivity analysis only.

    This is the formula actually implemented in v11:
        alpha * msp_used + (1 - alpha) * (1 - tsce)
    """
    return float(alpha * msp_used + (1.0 - alpha) * (1.0 - tsce))


def tune_cocoa_alpha(
    vce_vals: np.ndarray,
    sc_agree_vals: np.ndarray,
    corr: np.ndarray,
    alphas: Optional[np.ndarray] = None,
) -> Tuple[float, float]:
    """
    Tune alpha per model on holdout to minimize equal-width ECE.

    Parameters
    ----------
    vce_vals : np.ndarray
        Verbalized confidence estimates on [0, 1].
    sc_agree_vals : np.ndarray
        Self-consistency agreement fractions on [0, 1].
    corr : np.ndarray
        Binary correctness labels.
    alphas : np.ndarray, optional
        Candidate alpha grid (default: 0.1, 0.2, ..., 0.9).

    Returns
    -------
    best_alpha, best_ece
    """
    vce_vals = np.asarray(vce_vals, dtype=float)
    sc_agree_vals = np.asarray(sc_agree_vals, dtype=float)
    corr = np.asarray(corr, dtype=float)
    if alphas is None:
        alphas = np.arange(0.1, 1.0, 0.1)

    best_a, best_ece = 0.5, 1.0
    for a in alphas:
        mixed = a * vce_vals + (1.0 - a) * sc_agree_vals
        ece, _ = compute_ece_equal_width(mixed, corr)
        if ece < best_ece:
            best_ece = ece
            best_a = float(a)
    return best_a, float(best_ece)


# ---------------------------------------------------------------------------
# H3 test battery
# ---------------------------------------------------------------------------
def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Cliff's delta effect size for stochastic dominance of x over y."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.0
    # Vectorized comparison
    comparisons = np.sum(x[:, None] > y[None, :]) - np.sum(x[:, None] < y[None, :])
    return float(comparisons) / (nx * ny)


def bootstrap_ci(
    statistic_fn,
    data_x: np.ndarray,
    data_y: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    """
    Bootstrap percentile confidence interval for a two-sample statistic.

    Parameters
    ----------
    statistic_fn : callable
        Function(stat_x, stat_y) -> float.
    data_x, data_y : array-like
        Observations for the two groups.
    n_boot : int
        Number of bootstrap replications.
    ci : float
        Desired coverage (default 0.95).
    rng : np.random.Generator, optional
        Random generator for reproducibility.

    Returns
    -------
    (low, high) tuple or (np.nan, np.nan) if insufficient data.
    """
    x = np.asarray(data_x, dtype=float)
    y = np.asarray(data_y, dtype=float)
    x = x[np.isfinite(x)]
    y = y[np.isfinite(y)]
    if len(x) < 3 or len(y) < 3:
        return float("nan"), float("nan")
    if rng is None:
        rng = np.random.default_rng(42)
    boot = []
    for _ in range(n_boot):
        bx = rng.choice(x, size=len(x), replace=True)
        by = rng.choice(y, size=len(y), replace=True)
        boot.append(float(statistic_fn(bx, by)))
    boot = np.asarray(boot)
    alpha = 1 - ci
    return float(np.quantile(boot, alpha / 2)), float(np.quantile(boot, 1 - alpha / 2))


def cohens_d_ci(
    x: np.ndarray,
    y: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    """Bootstrap confidence interval for Cohen's d (x - y)."""

    def _d(a, b):
        pooled_sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        return (a.mean() - b.mean()) / (pooled_sd + 1e-9)

    return bootstrap_ci(_d, x, y, n_boot=n_boot, ci=ci, rng=rng)


def cliffs_delta_ci(
    x: np.ndarray,
    y: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[float, float]:
    """Bootstrap confidence interval for Cliff's delta (x vs y)."""
    return bootstrap_ci(cliffs_delta, x, y, n_boot=n_boot, ci=ci, rng=rng)


def holm_bonferroni(pvalues: np.ndarray) -> np.ndarray:
    """
    Holm-Bonferroni correction for multiple comparisons.

    Returns an array of corrected p-values with the same shape as the input.
    NaN values are left unchanged.
    """
    p = np.asarray(pvalues, dtype=float)
    if p.size == 0:
        return p
    flat = p.ravel().copy()
    nan_mask = ~np.isfinite(flat)
    valid_mask = ~nan_mask
    if valid_mask.sum() == 0:
        return p
    valid_idx = np.where(valid_mask)[0]
    valid_p = flat[valid_idx]
    order = np.argsort(valid_p)
    sorted_p = valid_p[order]
    n = len(sorted_p)
    stepwise = sorted_p * (n - np.arange(n))
    stepwise = np.minimum(stepwise, 1.0)  # cap individual multipliers at 1
    corrected = np.maximum.accumulate(stepwise)  # monotonically non-decreasing
    corrected = np.minimum(corrected, 1.0)
    # Unsort
    back = np.empty_like(sorted_p)
    back[order] = corrected
    flat[valid_idx] = back
    return flat.reshape(p.shape)


def compute_vif(df: pd.DataFrame, cols: List[str]) -> Dict[str, float]:
    """
    Compute variance inflation factors for a set of regressors.

    Returns a dict mapping column name to VIF. High VIF (>5-10) indicates
    multicollinearity.
    """
    vifs = {}
    for col in cols:
        others = [c for c in cols if c != col]
        if not others:
            vifs[col] = 1.0
            continue
        X = df[others].astype(float)
        y = df[col].astype(float)
        X = sm.add_constant(X, has_constant="add")
        try:
            model = sm.OLS(y, X).fit()
            r2 = model.rsquared
            vifs[col] = float(1.0 / max(1e-12, 1.0 - r2))
        except Exception:
            vifs[col] = float("nan")
    return vifs


def h3_test_battery(
    africa_wrong_conf: np.ndarray,
    europe_wrong_conf: np.ndarray,
) -> Dict:
    """
    Run the full H3 test battery on wrong-answer confidence values.

    Returns a dictionary with descriptive statistics, Welch's t-test,
    Mann-Whitney U, Cohen's d, and Cliff's delta.
    """
    af = np.asarray(africa_wrong_conf, dtype=float)
    eu = np.asarray(europe_wrong_conf, dtype=float)
    af = af[np.isfinite(af)]
    eu = eu[np.isfinite(eu)]

    result = {
        "n_af": len(af),
        "n_eu": len(eu),
        "af_mean": float(af.mean()) if len(af) else None,
        "eu_mean": float(eu.mean()) if len(eu) else None,
        "af_median": float(np.median(af)) if len(af) else None,
        "eu_median": float(np.median(eu)) if len(eu) else None,
    }

    if len(af) < 3 or len(eu) < 3:
        result["status"] = "SKIP (insufficient observations)"
        return result

    # Welch's t-test (two-sided reported; one-sided derived as half)
    t_stat, p_welch_two = stats.ttest_ind(af, eu, equal_var=False, alternative="two-sided")
    p_welch_one = p_welch_two / 2.0 if t_stat > 0 else 1.0 - p_welch_two / 2.0

    # Mann-Whitney U (two-sided reported; one-sided derived)
    u_stat, p_mann_two = stats.mannwhitneyu(af, eu, alternative="two-sided")
    # For one-sided p, use the rank-sum direction. scipy's two-sided p is
    # symmetric; we half it when the sample ordering matches the alternative.
    p_mann_one = p_mann_two / 2.0 if af.mean() > eu.mean() else 1.0 - p_mann_two / 2.0

    # Cohen's d with pooled SD
    pooled_sd = np.sqrt((af.var(ddof=1) + eu.var(ddof=1)) / 2)
    cohens_d = float((af.mean() - eu.mean()) / (pooled_sd + 1e-9))

    # Cliff's delta
    cd = cliffs_delta(af, eu)

    # Bootstrap confidence intervals
    d_low, d_high = cohens_d_ci(af, eu, rng=np.random.default_rng(42))
    cd_low, cd_high = cliffs_delta_ci(af, eu, rng=np.random.default_rng(42))

    result.update(
        {
            "welch_t": float(t_stat),
            "welch_p_one_sided": float(p_welch_one),
            "welch_p_two_sided": float(p_welch_two),
            "mannwhitney_u": float(u_stat),
            "mannwhitney_p_one_sided": float(p_mann_one),
            "mannwhitney_p_two_sided": float(p_mann_two),
            "cohens_d": cohens_d,
            "cohens_d_ci_low": d_low,
            "cohens_d_ci_high": d_high,
            "cliffs_delta": cd,
            "cliffs_delta_ci_low": cd_low,
            "cliffs_delta_ci_high": cd_high,
            # Legacy keys preserved for backward compatibility
            "welch_p": float(p_welch_one),
            "mannwhitney_p": float(p_mann_one),
            "status": "SUPPORTED" if p_mann_one < 0.05 else "not supported",
        }
    )
    return result


def fit_mixed_effects(
    df: pd.DataFrame,
    conf_col: str = "conf",
    region_col: str = "region",
    model_col: str = "model",
    qid_col: str = "qid",
    baseline_conf_col: Optional[str] = None,
) -> Dict:
    """
    Fit a linear mixed-effects model on wrong-answer confidence.

    Model: conf ~ region + model + (1 | qid)
    Optionally adds baseline_conf_col as a covariate.

    Returns a dictionary with coefficients, standard errors, z-values, p-values,
    ICC, and convergence status.
    """
    if not HAS_STATSMODELS:
        return {
            "error": "statsmodels not installed; mixed-effects model unavailable",
            "converged": False,
        }

    df = pd.DataFrame(df).copy()
    # Ensure region is coded Africa=1, Europe=0
    df["region_code"] = (df[region_col] == "Africa").astype(int)
    # One-hot encode model (drop first to avoid collinearity)
    model_dummies = pd.get_dummies(df[model_col], prefix="model", drop_first=True).astype(float)
    df = pd.concat([df, model_dummies], axis=1)

    fixed_cols = ["region_code"] + list(model_dummies.columns)
    if baseline_conf_col and baseline_conf_col in df.columns:
        df["baseline_conf"] = df[baseline_conf_col].astype(float)
        fixed_cols.append("baseline_conf")

    # Drop rows with missing values in fixed/random columns
    keep_cols = fixed_cols + [conf_col, qid_col]
    df_clean = df[keep_cols].dropna()
    if len(df_clean) == 0:
        return {"error": "no valid observations", "converged": False}

    y = df_clean[conf_col].astype(float)
    X = df_clean[fixed_cols].astype(float)
    X = sm.add_constant(X, has_constant="add").astype(float)
    groups = df_clean[qid_col].astype("category").cat.codes.astype(int)

    try:
        model = sm.MixedLM(y, X, groups=groups)
        fitted = model.fit(reml=False)
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc), "converged": False}

    # Intraclass correlation coefficient
    re_var = fitted.cov_re.iloc[0, 0] if hasattr(fitted.cov_re, "iloc") else float(fitted.cov_re)
    resid_var = fitted.scale
    icc = re_var / (re_var + resid_var) if (re_var + resid_var) > 0 else 0.0

    coefs = fitted.params.to_dict()
    ses = fitted.bse.to_dict()
    pvalues = fitted.pvalues.to_dict()
    zvalues = (fitted.params / fitted.bse).to_dict()

    return {
        "converged": fitted.converged,
        "n_obs": len(df_clean),
        "n_groups": len(np.unique(groups)),
        "icc": float(icc),
        "re_var": float(re_var),
        "resid_var": float(resid_var),
        "loglike": float(fitted.llf),
        "aic": float(fitted.aic),
        "bic": float(fitted.bic),
        "coefficients": coefs,
        "standard_errors": ses,
        "z_values": zvalues,
        "p_values": pvalues,
    }
