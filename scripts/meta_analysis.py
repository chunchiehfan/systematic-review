#!/usr/bin/env python3
"""
Meta-analysis statistical calculations using DerSimonian-Laird random effects.

Supports effect measures: OR, RR, MD, SMD, HR, PROP (pooled proportion)

Usage:
    python meta_analysis.py extracted_data.csv --measure OR --output meta_results.json

CSV column requirements by measure:
  OR/RR:  study, events_treatment, total_treatment, events_control, total_control
  MD/SMD: study, mean_treatment, sd_treatment, n_treatment, mean_control, sd_control, n_control
  HR:     study, hr, lower_ci, upper_ci
  PROP:   study, events, total
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Effect size calculations (return log-scale effect, variance for OR/RR/HR)
# ---------------------------------------------------------------------------

def calc_or(a: float, n1: float, c: float, n2: float):
    """Log odds ratio and its variance. Haldane-Anscombe correction for zeros."""
    b = n1 - a
    d = n2 - c
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    log_or = math.log(a * d / (b * c))
    var = 1/a + 1/b + 1/c + 1/d
    return log_or, var


def calc_rr(a: float, n1: float, c: float, n2: float):
    """Log risk ratio and its variance. Haldane-Anscombe correction for zeros."""
    if a == 0 or c == 0:
        a, c, n1, n2 = a + 0.5, c + 0.5, n1 + 0.5, n2 + 0.5
    log_rr = math.log((a / n1) / (c / n2))
    var = (1/a - 1/n1) + (1/c - 1/n2)
    return log_rr, var


def calc_md(mean1: float, sd1: float, n1: int, mean2: float, sd2: float, n2: int):
    """Mean difference and its variance."""
    md = mean1 - mean2
    var = (sd1 ** 2 / n1) + (sd2 ** 2 / n2)
    return md, var


def calc_smd(mean1: float, sd1: float, n1: int, mean2: float, sd2: float, n2: int):
    """Hedges' g (bias-corrected SMD) and its variance."""
    sd_pooled = math.sqrt(((n1 - 1) * sd1 ** 2 + (n2 - 1) * sd2 ** 2) / (n1 + n2 - 2))
    if sd_pooled == 0:
        raise ValueError("Pooled SD is zero — check input data.")
    d = (mean1 - mean2) / sd_pooled
    # Small-sample correction factor J (Hedges' g)
    df = n1 + n2 - 2
    j = 1 - 3 / (4 * df - 1)
    g = j * d
    var_g = (n1 + n2) / (n1 * n2) + g ** 2 / (2 * (n1 + n2 - 2))
    return g, var_g


def calc_hr(hr: float, lower_ci: float, upper_ci: float, ci_level: float = 0.95):
    """Log hazard ratio and variance derived from reported CI."""
    z = _z_from_ci(ci_level)
    log_hr = math.log(hr)
    se = (math.log(upper_ci) - math.log(lower_ci)) / (2 * z)
    return log_hr, se ** 2


def calc_prop_logit(events: float, total: float):
    """
    Logit-transformed proportion and variance for single-arm pooled proportion.
    Back-transform with logit_inv(x) = exp(x) / (1 + exp(x)).
    """
    # Continuity correction for boundary cases
    if events == 0:
        events = 0.5
    if events >= total:
        events = total - 0.5
    p = events / total
    logit_p = math.log(p / (1 - p))
    var = 1 / (events) + 1 / (total - events)
    return logit_p, var


def logit_inv(x: float) -> float:
    """Inverse logit (sigmoid) function."""
    return math.exp(x) / (1 + math.exp(x))


def _z_from_ci(ci_level: float = 0.95) -> float:
    """Z-score for a given confidence level (e.g., 0.95 -> 1.96)."""
    # Common values
    if abs(ci_level - 0.95) < 1e-6:
        return 1.959964
    if abs(ci_level - 0.99) < 1e-6:
        return 2.575829
    if abs(ci_level - 0.90) < 1e-6:
        return 1.644854
    # General case using scipy if available
    try:
        from scipy import stats
        return stats.norm.ppf((1 + ci_level) / 2)
    except ImportError:
        return 1.959964  # Fall back to 1.96


# ---------------------------------------------------------------------------
# DerSimonian-Laird random effects
# ---------------------------------------------------------------------------

def dersimonian_laird(effects: list, variances: list) -> dict:
    """
    DerSimonian-Laird random-effects meta-analysis.
    All inputs on the same scale (log scale for OR/RR/HR).
    Returns a dict with pooled estimate, CI, heterogeneity stats.
    """
    k = len(effects)
    if k < 2:
        raise ValueError(f"Meta-analysis requires at least 2 studies. Got {k}.")

    # Fixed-effects (inverse variance) weights
    w_fe = [1.0 / v for v in variances]
    w_sum = sum(w_fe)
    theta_fe = sum(w * y for w, y in zip(w_fe, effects)) / w_sum

    # Cochran's Q
    Q = sum(w * (y - theta_fe) ** 2 for w, y in zip(w_fe, effects))
    df = k - 1

    # tau² (DerSimonian-Laird estimator)
    C = w_sum - sum(w ** 2 for w in w_fe) / w_sum
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0

    # Random-effects weights
    w_re = [1.0 / (v + tau2) for v in variances]
    w_re_sum = sum(w_re)
    theta_re = sum(w * y for w, y in zip(w_re, effects)) / w_re_sum
    se_re = math.sqrt(1.0 / w_re_sum)

    z = _z_from_ci(0.95)
    ci_lower = theta_re - z * se_re
    ci_upper = theta_re + z * se_re

    # I² (Higgins 2003)
    i2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0

    # Q p-value
    q_pvalue = _chi2_pvalue(Q, df)

    # Weights as percentage of total
    weights_pct = [w / w_re_sum * 100.0 for w in w_re]

    return {
        "k": k,
        "theta_re": theta_re,
        "se_re": se_re,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "theta_fe": theta_fe,
        "Q": Q,
        "df": df,
        "Q_pvalue": q_pvalue,
        "I2": i2,
        "tau2": tau2,
        "tau": math.sqrt(tau2),
        "weights_pct": weights_pct,
    }


def _chi2_pvalue(Q: float, df: int) -> float:
    """Chi-squared right-tail p-value."""
    try:
        from scipy import stats
        return float(1 - stats.chi2.cdf(Q, df))
    except ImportError:
        # Rough approximation without scipy
        # Use normal approximation for large df
        if df <= 0:
            return 1.0
        z = math.sqrt(2 * Q) - math.sqrt(2 * df - 1)
        return max(0.0, 1 - _standard_normal_cdf(z))


def _standard_normal_cdf(x: float) -> float:
    """Approximation of the standard normal CDF."""
    return (1 + math.erf(x / math.sqrt(2))) / 2


# ---------------------------------------------------------------------------
# Publication bias: Egger's test
# ---------------------------------------------------------------------------

def egger_test(effects: list, variances: list) -> dict:
    """
    Egger's test for funnel plot asymmetry.
    Regresses standardized effect (effect/SE) on precision (1/SE).
    A significant non-zero intercept suggests publication bias.
    """
    k = len(effects)
    if k < 3:
        return {
            "note": "Egger's test requires ≥ 3 studies.",
            "k": k,
            "intercept": None,
            "se_intercept": None,
            "t_stat": None,
            "pvalue": None,
            "interpretation": "Cannot assess — insufficient studies.",
        }

    ses = [math.sqrt(v) for v in variances]
    precisions = [1.0 / se for se in ses]
    std_effects = [e / se for e, se in zip(effects, ses)]

    n = k
    x_mean = sum(precisions) / n
    y_mean = sum(std_effects) / n

    sxx = sum((x - x_mean) ** 2 for x in precisions)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(precisions, std_effects))

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean

    residuals = [y - (intercept + slope * x) for x, y in zip(precisions, std_effects)]
    mse = sum(r ** 2 for r in residuals) / (n - 2)
    se_intercept = math.sqrt(mse * (1.0 / n + x_mean ** 2 / sxx))

    if se_intercept == 0:
        return {"note": "Cannot compute Egger's test (degenerate data).", "pvalue": None}

    t_stat = intercept / se_intercept
    pvalue = _t_pvalue(abs(t_stat), df=n - 2)

    return {
        "k": k,
        "intercept": round(intercept, 4),
        "se_intercept": round(se_intercept, 4),
        "t_stat": round(t_stat, 4),
        "pvalue": round(pvalue, 4),
        "interpretation": (
            "Significant funnel asymmetry detected (p < 0.05) — possible publication bias."
            if pvalue < 0.05
            else "No significant funnel asymmetry (p ≥ 0.05)."
        ),
    }


def _t_pvalue(t: float, df: int) -> float:
    """Two-tailed t-test p-value."""
    try:
        from scipy import stats
        return float(2 * (1 - stats.t.cdf(t, df=df)))
    except ImportError:
        # Use normal approximation for large df
        return max(0.0, 2 * (1 - _standard_normal_cdf(t)))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

MEASURE_CALCULATORS = {
    "OR": lambda row: calc_or(
        float(row["events_treatment"]), float(row["total_treatment"]),
        float(row["events_control"]), float(row["total_control"]),
    ),
    "RR": lambda row: calc_rr(
        float(row["events_treatment"]), float(row["total_treatment"]),
        float(row["events_control"]), float(row["total_control"]),
    ),
    "MD": lambda row: calc_md(
        float(row["mean_treatment"]), float(row["sd_treatment"]), int(row["n_treatment"]),
        float(row["mean_control"]), float(row["sd_control"]), int(row["n_control"]),
    ),
    "SMD": lambda row: calc_smd(
        float(row["mean_treatment"]), float(row["sd_treatment"]), int(row["n_treatment"]),
        float(row["mean_control"]), float(row["sd_control"]), int(row["n_control"]),
    ),
    "HR": lambda row: calc_hr(
        float(row["hr"]), float(row["lower_ci"]), float(row["upper_ci"]),
    ),
    "PROP": lambda row: calc_prop_logit(float(row["events"]), float(row["total"])),
}

NEEDS_EXP = {"OR", "RR", "HR"}  # back-transform via exp()
NEEDS_LOGIT_INV = {"PROP"}       # back-transform via logit_inv()


def run_meta_analysis(data: list, measure: str) -> dict:
    """Run full random-effects meta-analysis on extracted data."""
    calc = MEASURE_CALCULATORS.get(measure)
    if not calc:
        raise ValueError(f"Unknown measure '{measure}'. Choose from: {list(MEASURE_CALCULATORS)}")

    effects, variances, study_rows = [], [], []

    for row in data:
        study_name = row.get("study") or row.get("Study") or f"Study {len(effects)+1}"
        try:
            effect, var = calc(row)
            effects.append(effect)
            variances.append(var)
            study_rows.append({"study": study_name, "effect_log": effect, "var": var})
        except (KeyError, ValueError, ZeroDivisionError, TypeError) as e:
            print(f"  Skipping '{study_name}': {e}", file=sys.stderr)

    if not effects:
        raise RuntimeError("No studies could be processed. Check CSV columns and values.")

    pooled = dersimonian_laird(effects, variances)
    egger = egger_test(effects, variances)
    z = _z_from_ci(0.95)

    def back_transform(x):
        if measure in NEEDS_EXP:
            return math.exp(x)
        elif measure in NEEDS_LOGIT_INV:
            return logit_inv(x)
        return x

    # Build per-study results
    studies_out = []
    for i, (row, effect, var) in enumerate(zip(study_rows, effects, variances)):
        se = math.sqrt(var)
        ci_lo = effect - z * se
        ci_hi = effect + z * se
        studies_out.append({
            "study": row["study"],
            "effect_log": round(effect, 5) if measure in NEEDS_EXP | NEEDS_LOGIT_INV else None,
            "effect": round(back_transform(effect), 4),
            "ci_lower": round(back_transform(ci_lo), 4),
            "ci_upper": round(back_transform(ci_hi), 4),
            "se": round(se, 5),
            "weight_pct": round(pooled["weights_pct"][i], 2),
            # Raw log-scale values for figure generation
            "_effect_raw": effect,
            "_ci_lower_raw": ci_lo,
            "_ci_upper_raw": ci_hi,
            "_se_raw": se,
        })

    pooled_effect_display = back_transform(pooled["theta_re"])
    pooled_ci_lo_display = back_transform(pooled["ci_lower"])
    pooled_ci_hi_display = back_transform(pooled["ci_upper"])

    # Interpretation of heterogeneity
    i2 = pooled["I2"]
    if i2 < 25:
        hetero_label = "low"
    elif i2 < 75:
        hetero_label = "moderate"
    else:
        hetero_label = "high (pooled estimate should be interpreted cautiously)"

    result = {
        "measure": measure,
        "k": pooled["k"],
        "pooled": {
            "effect": round(pooled_effect_display, 4),
            "ci_lower": round(pooled_ci_lo_display, 4),
            "ci_upper": round(pooled_ci_hi_display, 4),
            "se": round(pooled["se_re"], 5),
            # Log-scale values for forest plot
            "_effect_raw": pooled["theta_re"],
            "_ci_lower_raw": pooled["ci_lower"],
            "_ci_upper_raw": pooled["ci_upper"],
        },
        "fixed_effects": {
            "effect": round(back_transform(pooled["theta_fe"]), 4),
        },
        "heterogeneity": {
            "Q": round(pooled["Q"], 3),
            "df": pooled["df"],
            "Q_pvalue": round(pooled["Q_pvalue"], 4),
            "I2": round(i2, 1),
            "I2_label": hetero_label,
            "tau2": round(pooled["tau2"], 5),
            "tau": round(pooled["tau"], 5),
        },
        "publication_bias": egger,
        "studies": studies_out,
    }
    return result


def print_summary(result: dict):
    """Print a human-readable summary to stdout."""
    m = result["measure"]
    p = result["pooled"]
    h = result["heterogeneity"]
    pb = result["publication_bias"]

    print(f"\n{'='*60}")
    print(f"  Meta-Analysis Results ({m})")
    print(f"{'='*60}")
    print(f"  Studies (k):     {result['k']}")
    print(f"  Pooled {m:<5}:   {p['effect']:.3f}  (95% CI: {p['ci_lower']:.3f} – {p['ci_upper']:.3f})")
    print(f"\n  Heterogeneity:")
    print(f"    I²            = {h['I2']:.1f}%  ({h['I2_label']})")
    print(f"    τ²            = {h['tau2']:.4f}")
    print(f"    τ             = {h['tau']:.4f}")
    print(f"    Q ({h['df']} df)     = {h['Q']:.2f}  (p = {h['Q_pvalue']:.4f})")
    print(f"\n  Publication Bias (Egger's test):")
    if pb.get("pvalue") is not None:
        print(f"    Intercept     = {pb['intercept']:.4f}  (SE = {pb['se_intercept']:.4f})")
        print(f"    t-statistic   = {pb['t_stat']:.4f}")
        print(f"    p-value       = {pb['pvalue']:.4f}")
        print(f"    Interpretation: {pb['interpretation']}")
    else:
        print(f"    {pb.get('note', pb.get('interpretation', ''))}")
    print(f"{'='*60}\n")

    print(f"  Per-study results:")
    print(f"  {'Study':<30} {'Effect':>8} {'95% CI':>20} {'Weight':>8}")
    print(f"  {'-'*70}")
    for s in result["studies"]:
        print(f"  {s['study']:<30} {s['effect']:>8.3f}  [{s['ci_lower']:.3f}, {s['ci_upper']:.3f}]  {s['weight_pct']:>6.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Run DerSimonian-Laird random-effects meta-analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="CSV file with extracted study data")
    parser.add_argument(
        "--measure",
        required=True,
        choices=["OR", "RR", "MD", "SMD", "HR", "PROP"],
        help="Effect measure type",
    )
    parser.add_argument(
        "--output",
        default="meta_results.json",
        help="Output JSON file (default: meta_results.json)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = list(reader)

    print(f"Loaded {len(data)} studies from {input_path}")
    print(f"Running {args.measure} meta-analysis...")

    result = run_meta_analysis(data, args.measure)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2))
    print(f"Results saved to {output_path}")

    print_summary(result)


if __name__ == "__main__":
    main()
