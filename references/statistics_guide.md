# Statistical Methods Reference for Meta-Analysis

## Effect Measures

### Binary Outcomes

**Odds Ratio (OR)**
- Range: 0 to ∞; null value = 1.0
- OR = (a/b) / (c/d) where a=events treatment, b=non-events treatment, c=events control, d=non-events control
- Log transform for analysis: ln(OR); back-transform with exp()
- Use when: case-control studies, rare outcomes (<10%), logistic regression results
- Variance of ln(OR) = 1/a + 1/b + 1/c + 1/d

**Risk Ratio / Relative Risk (RR)**
- Range: 0 to ∞; null value = 1.0
- RR = [a/(a+b)] / [c/(c+d)]
- Use when: cohort studies or RCTs with common events (>10%), absolute risk is meaningful
- Variance of ln(RR) = (1/a - 1/n1) + (1/c - 1/n2)
- Note: OR ≈ RR only when event rates are low (<10%)

**Haldane-Anscombe correction**
- Add 0.5 to all cells (a, b, c, d) when any cell = 0
- Required to avoid division by zero or log(0)

### Continuous Outcomes

**Mean Difference (MD)**
- Used when all studies report the same scale/units
- MD = mean_treatment − mean_control; null value = 0
- Variance = SD1²/n1 + SD2²/n2

**Standardized Mean Difference (SMD) / Hedges' g**
- Use when studies measure same construct on different scales
- d = (mean1 − mean2) / SD_pooled  (Cohen's d)
- Hedges' g = J × d, where J = 1 − 3/(4df − 1)  [small-sample correction]
- Interpretation: small ≈ 0.2, medium ≈ 0.5, large ≈ 0.8
- Variance = (n1+n2)/(n1×n2) + g²/(2×(n1+n2−2))

### Survival / Time-to-Event

**Hazard Ratio (HR)**
- Range: 0 to ∞; null value = 1.0
- Usually reported directly from Cox regression with 95% CI
- Derive log(HR) and SE from: SE = [ln(upper) − ln(lower)] / (2 × 1.96)
- Assumes proportional hazards

### Single-Arm Proportions

**Logit transformation (preferred)**
- logit(p) = ln(p / (1−p)); back-transform: exp(x) / (1 + exp(x))
- Variance = 1/events + 1/(total − events)
- More stable for proportions 0.1–0.9

---

## Pooling Models

### Fixed-Effects (Inverse Variance)
- Assumption: one true underlying effect; all variation is sampling error
- Weight: w_i = 1/var_i
- Pooled estimate: θ_FE = Σ(w_i × y_i) / Σw_i
- Use when: studies are very homogeneous, specifically planned as replications

### Random Effects (DerSimonian-Laird) — PRIMARY MODEL
- Assumption: true effect varies between studies (between-study heterogeneity exists)
- More conservative (wider CI), more generalizable
- tau² (between-study variance): τ² = max(0, (Q − df) / C)
  - C = Σw_i − Σw_i² / Σw_i
- RE weights: w_i* = 1/(var_i + τ²)
- Pooled estimate: θ_RE = Σ(w_i* × y_i) / Σw_i*
- SE = sqrt(1 / Σw_i*)

**When to choose RE over FE:** Almost always. Use FE only when you have strong prior reasons to assume a single true effect.

---

## Heterogeneity

**Cochran's Q statistic**
- Q = Σ w_i × (y_i − θ_FE)²
- Distributed as χ² with df = k−1 under null of homogeneity
- Low power with few studies; high power with many studies

**I² statistic (Higgins 2003)**
- I² = max(0, (Q − df) / Q × 100%)
- Proportion of total variance due to between-study heterogeneity
- Interpretation (approximate, context-dependent):
  - 0–25%: low heterogeneity
  - 25–75%: moderate — explore potential sources
  - >75%: high — pooled estimate may be misleading; consider narrative synthesis

**τ² (tau-squared)**
- The estimated between-study variance on the effect scale
- τ (tau) = √τ² is the SD of true effects; useful for prediction interval
- 95% Prediction interval = θ_RE ± 1.96 × √(SE² + τ²)

**When I² > 75%:**
1. Identify potential sources (subgroup analysis, meta-regression)
2. Report narrative synthesis alongside pooled estimate
3. Consider whether pooling is appropriate at all

---

## Publication Bias

**Funnel plot**
- Plot effect size (x) vs. standard error (y, inverted)
- Symmetric funnel = no bias; asymmetry = possible small-study effect
- Visual inspection is subjective; use Egger's test for quantification

**Egger's test**
- Regresses standardized effect (effect/SE) on precision (1/SE)
- Intercept significantly ≠ 0 → asymmetry present
- p < 0.05 suggests possible publication bias
- Low power with k < 10 studies

**Trim-and-fill**
- Iteratively removes asymmetric studies and imputes "missing" ones
- Provides adjusted pooled estimate under no-bias scenario
- Not implemented in script; compute manually or use R/Stata

---

## Risk of Bias Tools

**RCTs: Cochrane RoB 2 (2019)**
- Domain 1: Randomization process
- Domain 2: Deviations from intended interventions
- Domain 3: Missing outcome data
- Domain 4: Measurement of the outcome
- Domain 5: Selection of reported results
- Overall: Low / Some concerns / High

**Observational: Newcastle-Ottawa Scale (NOS)**
- Cohort: Selection (4 items) + Comparability (2) + Outcome (3) = max 9 stars
- Case-control: Selection (4) + Comparability (2) + Exposure (3) = max 9 stars
- ≥7 stars = low risk of bias

---

## GRADE Evidence Quality

Start at High for RCTs, Moderate for observational.

| Factor | Downgrade |
|--------|-----------|
| Risk of bias (mostly high RoB) | −1 or −2 |
| Inconsistency (I² > 50%) | −1; I² > 75% = −2 |
| Indirectness (different pop/intervention/outcome) | −1 or −2 |
| Imprecision (CI crosses null; total N < optimal) | −1 or −2 |
| Publication bias (Egger p < 0.05; funnel asymmetry) | −1 |

Final grades: **High** > **Moderate** > **Low** > **Very Low**

Upgrade criteria (for observational): large effect (RR > 2), dose-response, residual confounding would attenuate the effect.

---

## Reporting Standards

**PRISMA 2020 checklist items to address:**
- Abstract: structured with background, methods, results, conclusions
- Protocol registration (PROSPERO ID)
- Eligibility criteria (Population, Intervention, Comparison, Outcome, Study design)
- Information sources and search strategy (full string in supplementary)
- Data extraction process (dual independent extraction recommended)
- Risk of bias assessment method
- Effect measure and statistical model
- Heterogeneity assessment method
- Publication bias methods
- Funding and conflicts of interest

**Numbers to always report:**
- k (number of studies)
- N (total participants)
- Pooled effect with 95% CI and p-value
- I², τ², Q statistic with p-value
- Egger's test p-value
- GRADE evidence quality for each primary outcome
