---
name: systematic-review
description: >
  Conducts a full PRISMA 2020-compliant systematic review and meta-analysis on any medical or
  clinical topic. Use this skill when users ask to: perform a systematic review, run a
  meta-analysis, pool evidence across studies, review the literature on a medical/clinical
  question, create forest plots or funnel plots, assess publication bias, summarize evidence
  quality using GRADE, or conduct a literature synthesis. Trigger on phrases like:
  "systematic review", "meta-analysis", "forest plot", "pool the evidence", "PRISMA",
  "literature review on", "what does the evidence say about", "summarize studies on",
  "evidence synthesis", "I want to review the literature on X", "help me analyze studies about Y",
  "is there evidence for", "compare studies on". When users discuss medical interventions,
  outcomes, or ask about what research shows on a topic, lean toward invoking this skill.
---

# Systematic Review & Meta-Analysis

A 6-phase workflow following PRISMA 2020 guidelines. Each phase ends with a user checkpoint
before advancing. Scripts handle computation; Claude handles reasoning and writing.

## Setup

Create a project directory at the start:
```bash
mkdir -p ~/systematic-review-<topic-slug>
cd ~/systematic-review-<topic-slug>
```

Skill scripts are in `~/.claude/skills/systematic-review/scripts/`. Reference this path as
`SKILL_DIR=~/.claude/skills/systematic-review` throughout.

Required Python packages: `matplotlib scipy numpy`. Install if missing:
```bash
pip install matplotlib scipy numpy
```

---

## Phase 1: Topic Refinement

**Goal:** Convert a broad question into a precise PICO(S) question and a PubMed search string.

### Steps

1. Ask the user to state their research question if not already given.

2. Structure it using the PICO(S) framework:
   - **P** — Population (age group, diagnosis, setting, comorbidities)
   - **I** — Intervention (drug, procedure, exposure, diagnostic test)
   - **C** — Comparison (placebo, standard care, another intervention, or none)
   - **O** — Outcome(s): list primary outcome first, then secondary
   - **S** — Study design (RCTs only? Observational? Any?)

3. Suggest MeSH terms + free-text synonyms for each PICO element.

4. Build a Boolean PubMed search string. Example pattern:
   ```
   (MeSH-term[MeSH] OR synonym1[tiab] OR synonym2[tiab]) AND
   (MeSH-term2[MeSH] OR synonym3[tiab]) AND
   (outcome1[tiab] OR outcome2[tiab])
   ```

5. **Checkpoint:** Show the PICO table and search string. Ask the user to confirm or adjust
   before proceeding.

**Output:** `pico.md` — PICO table + confirmed search string + date.

---

## Phase 2: PubMed Literature Search

**Goal:** Retrieve all potentially eligible records from PubMed.

### Steps

1. Ask for the user's NCBI API key (gives 10 req/s vs 3 req/s). Set `--api-key` accordingly.

2. Run:
   ```bash
   python $SKILL_DIR/scripts/pubmed_search.py \
     "<search_string>" \
     --max-results 500 \
     --api-key <KEY_OR_OMIT> \
     --output pubmed_results.json
   ```

3. Report the number of records retrieved. If >500, discuss with user whether to narrow the
   search or increase `--max-results`.

4. Write `search_log.md`:
   ```markdown
   ## PubMed Search Log
   - Date: YYYY-MM-DD
   - Search string: <string>
   - Records retrieved: N
   - API key used: yes/no
   ```

5. Suggest supplementary databases for manual search: Embase, Cochrane, ClinicalTrials.gov,
   CINAHL. Note any that the user wants added.

**Checkpoint:** Confirm record count and databases before screening.

**Output:** `pubmed_results.json`, `search_log.md`

---

## Phase 3: Screening

**Goal:** Apply inclusion/exclusion criteria to identify eligible studies.

### Define criteria

Confirm with the user before screening. Present a template:

```
Inclusion criteria:
- Study designs: [RCTs / cohort / case-control / all]
- Population: [...]
- Intervention: [...]
- Comparator: [...]
- Outcomes: [...]
- Language: [English / all]
- Minimum follow-up: [...]

Exclusion criteria:
- Case reports, letters, editorials, conference abstracts (unless specified)
- [Other user-defined criteria]
```

### Screening process

Read `pubmed_results.json`. Screen each article against the criteria:

1. **Title/abstract screening:** Assign each article:
   - `include` — clearly meets criteria
   - `exclude` — clearly fails at least one criterion (state reason)
   - `uncertain` — cannot decide without full text

2. Save decisions to `screening_results.json`:
   ```json
   [
     {
       "pmid": "12345678",
       "title": "...",
       "authors": "Smith et al.",
       "year": "2020",
       "decision": "include",
       "reason": ""
     },
     {
       "pmid": "87654321",
       "title": "...",
       "decision": "exclude",
       "reason": "Wrong population: pediatric only"
     }
   ]
   ```

3. For **uncertain** articles: list them for the user with what information is needed.

4. Build `prisma_data.json` with flow counts:
   ```json
   {
     "identified": 450,
     "duplicates_removed": 0,
     "screened": 450,
     "excluded_screening": 390,
     "full_text_assessed": 60,
     "excluded_full_text": 42,
     "included": 18,
     "exclusion_reasons": [
       {"reason": "Wrong population", "n": 15},
       {"reason": "No comparator group", "n": 12},
       {"reason": "Insufficient data", "n": 10},
       {"reason": "Other", "n": 5}
     ]
   }
   ```

**Tip:** For reviews with >200 records, screen in batches of 20-30. Exclude obvious mismatches
first; this narrows the uncertain pool quickly.

**Checkpoint:** Show final counts. List uncertain articles. Get user decision before extraction.

**Output:** `screening_results.json`, `prisma_data.json`

---

## Phase 4: Data Extraction

**Goal:** Extract quantitative and qualitative data from each included study.

### Ask the user which effect measure to use:
- **OR** — binary outcome, odds ratio preferred (case-control or studies with low event rates)
- **RR** — binary outcome, risk ratio preferred (cohort/RCT with common events)
- **MD** — continuous outcome, same measurement scale across studies
- **SMD** — continuous outcome, different scales (produces Cohen's d / Hedges' g)
- **HR** — time-to-event outcome
- **PROP** — single-arm proportion (prevalence/incidence reviews)

### Extract study characteristics into `study_characteristics.csv`:
```csv
study,year,country,design,n_total,population,intervention,comparator,follow_up,primary_outcome,rob_score
Smith 2020,2020,USA,RCT,450,"Adults with T2DM","Empagliflozin 10 mg","Placebo","52 weeks","HbA1c change",Low
```

### Extract outcome data into `extracted_data.csv` based on effect measure:

**OR or RR:**
```csv
study,year,design,events_treatment,total_treatment,events_control,total_control,notes
Smith 2020,2020,RCT,45,230,67,225,
```

**MD or SMD:**
```csv
study,year,design,mean_treatment,sd_treatment,n_treatment,mean_control,sd_control,n_control,notes
Smith 2020,2020,RCT,-1.2,0.8,120,-0.3,0.7,118,HbA1c % change from baseline
```

**HR:**
```csv
study,year,design,hr,lower_ci,upper_ci,notes
Smith 2020,2020,RCT,0.72,0.58,0.89,
```

**PROP:**
```csv
study,year,design,events,total,notes
Smith 2020,2020,Cohort,45,230,
```

### Risk of Bias

- RCTs: Cochrane Risk of Bias 2 (RoB 2) — assess 5 domains → Low / Some concerns / High
- Observational: Newcastle-Ottawa Scale (0–9 stars)

Add a `rob_score` column (Low / Moderate / High) to `study_characteristics.csv`.

**Checkpoint:** Show the extracted data tables. Ask user to verify accuracy before analysis.

**Output:** `extracted_data.csv`, `study_characteristics.csv`

---

## Phase 5: Meta-Analysis

**Goal:** Pool effect estimates, quantify heterogeneity, assess publication bias.

### Run the meta-analysis

```bash
python $SKILL_DIR/scripts/meta_analysis.py \
  extracted_data.csv \
  --measure OR|RR|MD|SMD|HR|PROP \
  --output meta_results.json
```

This computes:
- **DerSimonian-Laird random-effects** as the primary model
- **Inverse-variance fixed-effects** as secondary
- **Cochran's Q**, **I²**, **τ²** for heterogeneity
- **Egger's test** for publication bias

### Generate figures

```bash
python $SKILL_DIR/scripts/generate_figures.py \
  meta_results.json \
  --forest forest_plot.png \
  --funnel funnel_plot.png \
  --prisma prisma_data.json \
  --prisma-out prisma_diagram.png \
  --title "<Review Title>"
```

### Interpret and report

| Metric | Interpretation |
|--------|---------------|
| I² < 25% | Low heterogeneity |
| I² 25–75% | Moderate heterogeneity — explore subgroups |
| I² > 75% | High heterogeneity — interpret pooled estimate cautiously |
| Egger p < 0.05 | Possible publication bias — use trim-and-fill caveat |

**If k < 3 studies:** Do not pool. Perform narrative synthesis only.

**If I² > 75%:** Flag substantial heterogeneity. Explore subgroup analyses by study design,
population, or follow-up duration. Consider meta-regression if ≥10 studies.

**Sensitivity analysis:** Consider re-running excluding high-RoB studies and report both results.

**Checkpoint:** Show figure paths and key statistics. Discuss heterogeneity findings with user.

**Output:** `meta_results.json`, `forest_plot.png`, `funnel_plot.png`, `prisma_diagram.png`

---

## Phase 6: Report & Executive Summary

**Goal:** Synthesize all findings into a complete, readable report.

Create `systematic_review_report.md` following this structure:

```markdown
# Systematic Review: [Full Title]

**Date:** YYYY-MM-DD
**Search date:** YYYY-MM-DD
**PROSPERO registration:** [ID or "Not registered"]

---

## Executive Summary

[3–5 sentences: clinical question, number of studies, total N, key pooled effect with CI,
heterogeneity level, evidence quality (GRADE), and main clinical implication.]

---

## Background

[Why this question matters clinically. Current practice gaps. Scope of the review.]

---

## Methods

### Search strategy
[Databases, search string, date range, restrictions.]

### Eligibility criteria
| | Criteria |
|--|---------|
| **Population** | ... |
| **Intervention** | ... |
| **Comparator** | ... |
| **Outcomes** | ... |
| **Study designs** | ... |

### Data extraction and risk of bias
[Who extracted, what tool was used for RoB.]

### Statistical analysis
[Effect measure, model (DL random effects), heterogeneity stats, publication bias test,
software (Python/scipy).]

---

## Results

### Study selection
![PRISMA flow diagram](prisma_diagram.png)

### Study characteristics
[Paste study_characteristics.csv as markdown table]

### Risk of bias
[Summary: n studies low/moderate/high RoB]

### Meta-analysis: [Primary outcome]

- **Pooled [measure]:** [value] (95% CI: [lo]–[hi], p = [p])
- **Studies:** k = [N], participants: N = [N]
- **Heterogeneity:** I² = [X]%, τ² = [X], Q = [X] (p = [p])

![Forest plot](forest_plot.png)

**Publication bias**
- Egger's test: intercept = [X], p = [p]
- [Interpretation: "No significant funnel plot asymmetry detected" or flag concern]

![Funnel plot](funnel_plot.png)

### GRADE evidence summary

| Outcome | k | N | Effect | 95% CI | I² | RoB | Evidence quality |
|---------|---|---|--------|--------|----|-----|-----------------|
| [Primary] | | | | | | | High/Moderate/Low/Very Low |

---

## Discussion

[Interpretation in clinical context. Comparison to prior reviews. Limitations:
search scope, language bias, publication bias, heterogeneity. Strengths.]

---

## Conclusion

[One clear sentence summarizing the evidence and clinical implication.]

---

## Included Studies

[List with PMID: Author Year — Title — Journal]
```

### GRADE assessment guide
Start at **High** for RCTs, **Moderate** for observational. Downgrade 1 level per serious issue:
- Risk of bias (mostly high RoB studies)
- Inconsistency (I² > 50% = serious; > 75% = very serious)
- Indirectness (indirect population, intervention, or outcome)
- Imprecision (CI crosses null, small total N)
- Publication bias (Egger p < 0.05 + small study effects)

---

## Phase Summary

| Phase | Key files | User checkpoint |
|-------|-----------|----------------|
| 1. Topic refinement | `pico.md` | Confirm PICO + search string |
| 2. Literature search | `pubmed_results.json`, `search_log.md` | Confirm record count |
| 3. Screening | `screening_results.json`, `prisma_data.json` | Review uncertain papers |
| 4. Data extraction | `extracted_data.csv`, `study_characteristics.csv` | Verify data accuracy |
| 5. Meta-analysis | `meta_results.json`, PNG figures | Confirm heterogeneity interpretation |
| 6. Report | `systematic_review_report.md` | Final sign-off |

For statistical method details: `references/statistics_guide.md`
For extraction column definitions: `references/extraction_templates.md`
