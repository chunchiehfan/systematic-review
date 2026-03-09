# Data Extraction Templates

## Study Characteristics CSV

All included studies should be recorded here regardless of effect measure.

```
study,year,country,design,n_total,population,intervention,comparator,follow_up,primary_outcome,rob_score,rob_tool,funding,notes
```

**Column definitions:**
- `study`: First author + year (e.g., "Smith 2020")
- `year`: Publication year (integer)
- `country`: Country or "Multi-center"
- `design`: RCT / Prospective cohort / Retrospective cohort / Case-control / Cross-sectional
- `n_total`: Total enrolled participants
- `population`: Brief description (age, diagnosis, setting)
- `intervention`: Intervention arm description
- `comparator`: Control/comparison arm description
- `follow_up`: Duration (e.g., "12 weeks", "5 years")
- `primary_outcome`: Primary outcome as reported
- `rob_score`: Low / Moderate / High (your assessed overall risk of bias)
- `rob_tool`: RoB2 / NOS / Other
- `funding`: Industry / Government / Non-profit / Not reported / Mixed
- `notes`: Any important caveats

**Example:**
```csv
study,year,country,design,n_total,population,intervention,comparator,follow_up,primary_outcome,rob_score,rob_tool,funding
Smith 2020,2020,USA,RCT,450,"Adults ≥18 with T2DM","Empagliflozin 10 mg daily","Placebo","52 weeks","Change in HbA1c from baseline",Low,RoB2,Industry
Jones 2021,2021,UK,Cohort,1200,"T2DM patients in primary care","SGLT2 inhibitor (any)","No SGLT2 inhibitor","Median 3.2 years","MACE (composite)",Moderate,NOS,Government
```

---

## Outcome Data CSVs

### OR / RR (Binary outcome)

Columns: study, events_treatment, total_treatment, events_control, total_control, notes

```csv
study,events_treatment,total_treatment,events_control,total_control,notes
Smith 2020,45,230,67,225,
Jones 2021,12,89,28,91,Adjusted for age and sex
```

**What to extract:**
- `events_treatment`: Number experiencing the outcome in intervention arm
- `total_treatment`: Total in intervention arm
- `events_control`: Number experiencing outcome in control arm
- `total_control`: Total in control arm

**Finding the numbers:**
- Often in "Results" tables as n/N format (e.g., 45/230)
- May be in Kaplan-Meier table at specific time point
- Check supplementary tables if not in main text

---

### MD / SMD (Continuous outcome)

Columns: study, mean_treatment, sd_treatment, n_treatment, mean_control, sd_control, n_control, notes

```csv
study,mean_treatment,sd_treatment,n_treatment,mean_control,sd_control,n_control,notes
Smith 2020,-1.2,0.8,120,-0.3,0.7,118,HbA1c % change from baseline at 52 weeks
Jones 2021,-0.9,1.1,89,-0.1,0.9,91,
```

**What to extract:**
- Prefer **change from baseline** over endpoint values when studies differ
- Use **SD** (not SE or 95% CI) — convert if needed:
  - SE → SD: SD = SE × √n
  - 95% CI → SD: SD = (upper − lower) / (2 × 1.96) × √n
- If IQR reported: SD ≈ IQR / 1.35 (rough approximation for normally distributed data)

---

### HR (Survival / time-to-event)

Columns: study, hr, lower_ci, upper_ci, notes

```csv
study,hr,lower_ci,upper_ci,notes
Smith 2020,0.72,0.58,0.89,Adjusted HR from Cox regression
Jones 2021,0.85,0.70,1.03,
```

**What to extract:**
- Adjusted HR is preferred over unadjusted
- Ensure all HRs are in the same direction (treatment vs. control)
- Check that 95% CI is the 95% CI (not 90% or 99%)

---

### PROP (Single-arm proportions)

Columns: study, events, total, notes

```csv
study,events,total,notes
Smith 2020,45,230,30-day mortality
Jones 2021,12,89,
Brown 2022,103,650,ICU cohort
```

**What to extract:**
- Events = number with outcome
- Total = study population at baseline (not adjusted denominator)

---

## Risk of Bias: Cochrane RoB 2 (RCTs)

Record for each study:

| Study | D1: Randomization | D2: Deviations | D3: Missing data | D4: Outcome measurement | D5: Selective reporting | Overall |
|-------|-------------------|----------------|------------------|------------------------|------------------------|---------|
| Smith 2020 | Low | Low | Some concerns | Low | Low | Low |

**Domains:**
- D1: Was allocation sequence concealed? Were groups balanced at baseline?
- D2: Were participants/providers blinded? Any crossover or non-compliance?
- D3: Were all randomized participants included? Any differential dropout?
- D4: Was outcome assessor blinded? Subjective vs. objective outcomes?
- D5: Was the study analysis pre-specified? Any selective reporting?

---

## Risk of Bias: Newcastle-Ottawa Scale (Observational)

**For cohort studies (max 9 stars):**

| Study | Representativeness | Non-exposed cohort | Exposure ascertainment | Outcome not present at start | Comparability | Outcome assessment | Follow-up duration | Adequacy of follow-up | Total |
|-------|-------------------|--------------------|----------------------|------------------------------|---------------|-------------------|-------------------|----------------------|-------|
| Jones 2021 | ★ | ★ | ★ | ★ | ★★ | ★ | ★ | ★ | 9 |

Score ≥7 = low RoB; 4–6 = moderate; <4 = high.

---

## GRADE Evidence Summary Table Template

| Outcome | Studies (k) | Participants (N) | Pooled effect (95% CI) | RoB | Inconsistency (I²) | Indirectness | Imprecision | Publication bias | Evidence quality |
|---------|-------------|-----------------|----------------------|-----|-------------------|--------------|-------------|-----------------|-----------------|
| [Primary] | 8 | 4,250 | OR 0.72 (0.61–0.85) | Low | Low (I²=18%) | Not serious | Not serious | Undetected | **Moderate** |
| [Secondary] | 5 | 2,100 | MD −1.2 (−1.8 to −0.6) | Some concerns | Moderate (I²=45%) | Not serious | Serious | Undetected | **Low** |

---

## Data Extraction Checklist

Before finalizing extraction, verify:
- [ ] Same direction for all effects (e.g., all ORs favor treatment, or all show harm)
- [ ] Same time point used across studies (or note variation)
- [ ] SD vs. SE vs. CI correctly identified and converted
- [ ] n per arm (not total sample) used for MD/SMD
- [ ] Events are counts (not %) for OR/RR
- [ ] HR confidence level is 95% (not 90%)
- [ ] Risk of bias assessed independently for each outcome (not just per study)
- [ ] Missing studies investigated (contacted authors if possible)
