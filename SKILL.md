---
name: systematic-review
description: >
  Conducts a full PRISMA 2020-compliant systematic review and meta-analysis autonomously.
  Claude runs all 6 phases (topic refinement, PubMed search, screening, data extraction,
  meta-analysis, report) without stopping, logging every decision along the way. At the end,
  it presents a single draft report with embedded decision checkpoints for the user to review
  and override. Only phases affected by user changes are rerun. Use this skill when users ask
  to: perform a systematic review, run a meta-analysis, pool evidence across studies, review
  the literature on a medical/clinical question, create forest plots or funnel plots, assess
  publication bias, summarize evidence quality using GRADE, or conduct a literature synthesis.
  Trigger on phrases like: "systematic review", "meta-analysis", "forest plot", "pool the
  evidence", "PRISMA", "literature review on", "what does the evidence say about", "summarize
  studies on", "evidence synthesis", "I want to review the literature on X", "help me analyze
  studies about Y", "is there evidence for", "compare studies on". When users discuss medical
  interventions, outcomes, or ask about what research shows on a topic, lean toward invoking
  this skill.
---

# Systematic Review & Meta-Analysis (Autonomous)

A two-stage workflow following PRISMA 2020 guidelines. Stage 1 runs all 6 phases autonomously
with decision logging. Stage 2 presents a consolidated decision review for user approval, then
reruns only affected phases if changes are made.

## Setup

Create a project directory at the start:
```bash
mkdir -p ~/systematic-review-<topic-slug>
cd ~/systematic-review-<topic-slug>
```

Set `SKILL_DIR=~/.claude/skills/systematic-review` throughout.

Required Python packages: `matplotlib scipy numpy`. Install if missing:
```bash
pip install matplotlib scipy numpy
```

Import the decision logger at the start of Stage 1:
```python
from scripts.decisions_logger import DecisionLogger
logger = DecisionLogger("decisions_log.json")
```

---

## Stage 1: Autonomous Run

Run all 6 phases without stopping. At each point where user input would normally be needed,
make your best-judgment decision, log it with rationale, and continue. The user reviews
everything at the end.

### Phase 1: Topic Refinement

**Goal:** Convert the user's question into a PICO(S) question and PubMed search string.

1. Structure the user's question using PICO(S):
   - **P** — Population (age, diagnosis, setting, comorbidities)
   - **I** — Intervention (drug, procedure, exposure)
   - **C** — Comparison (placebo, standard care, another intervention)
   - **O** — Outcome(s): primary first, then secondary
   - **S** — Study design (RCTs, observational, all)

2. Select MeSH terms + free-text synonyms for each PICO element.

3. Build a Boolean PubMed search string.

4. Log all decisions:
   ```python
   logger.log(phase=1, key="pico_definition",
              value={"P": "...", "I": "...", "C": "...", "O": "...", "S": "..."},
              rationale="Derived from user prompt: ...", confidence="auto")
   logger.log(phase=1, key="search_string",
              value="(MeSH[MeSH] OR synonym[tiab]) AND ...",
              rationale="Combined MeSH + free-text for each PICO element", confidence="auto")
   logger.log(phase=1, key="study_design_filter",
              value="RCTs and cohort studies",
              rationale="User asked about effectiveness, included both for breadth", confidence="auto")
   ```

**Output:** `pico.md`

---

### Phase 2: PubMed Search + PMC Full-Text Fetch

**Goal:** Retrieve records from PubMed and fetch full text from PMC where available.

1. If the user provided an NCBI API key, use it. Otherwise proceed without (slower rate limit).

2. Run PubMed search:
   ```bash
   python $SKILL_DIR/scripts/pubmed_search.py "<search_string>" \
     --max-results 500 --api-key <KEY_OR_OMIT> --output pubmed_results.json
   ```

3. If >500 results, make a judgment call: narrow the search or increase max-results. Log the decision.

4. Fetch PMC full text for all retrieved articles:
   ```bash
   python $SKILL_DIR/scripts/pmc_fulltext.py pubmed_results.json \
     --output-dir fulltext_data/ --api-key <KEY_OR_OMIT>
   ```

5. Log decisions:
   ```python
   logger.log(phase=2, key="search_executed",
              value={"query": "...", "results": N, "max_results": 500},
              rationale="...", confidence="auto")
   logger.log(phase=2, key="no_fulltext_papers",
              value=["PMID1", "PMID2", ...],  # from fulltext_data/no_fulltext.json
              rationale="These PMIDs are not available in PMC. Screened on abstract only.",
              confidence="needs_review")
   ```

6. Write `search_log.md` with date, query, record count, API key status, PMC coverage.

**Output:** `pubmed_results.json`, `fulltext_data/`, `search_log.md`

---

### Phase 3: Screening

**Goal:** Apply inclusion/exclusion criteria using a confidence-tier system.

#### Define criteria

Based on the PICO from Phase 1, define inclusion/exclusion criteria:
- Study designs, population, intervention, comparator, outcomes, language, minimum follow-up
- Exclusions: case reports, letters, editorials, conference abstracts

#### Confidence-tier screening

Screen each article and assign a confidence tier:

- **Auto-exclude** (high confidence fail): Clearly fails at least one criterion. Log reason.
  No user review needed unless overridden.
- **Auto-include** (high confidence match): Clearly meets all criteria from title/abstract
  (or full text if available). Log reason.
- **Uncertain**: Cannot decide from available information. Make a best-guess decision and log
  what was ambiguous. For papers with PMC full text in `fulltext_data/`, use the full text
  to try to resolve uncertainty before marking as uncertain.

Save to `screening_results.json`:
```json
[
  {
    "pmid": "12345678",
    "title": "...",
    "authors": "Smith et al.",
    "year": "2020",
    "decision": "include",
    "confidence": "auto",
    "reason": "RCT of empagliflozin vs placebo in T2DM, reports HF hospitalization"
  },
  {
    "pmid": "87654321",
    "title": "...",
    "decision": "exclude",
    "confidence": "auto",
    "reason": "Pediatric population — outside PICO"
  },
  {
    "pmid": "11111111",
    "title": "...",
    "decision": "include",
    "confidence": "uncertain",
    "reason": "Abstract unclear on comparator arm; included based on full-text review showing placebo control"
  }
]
```

Log screening summary:
```python
logger.log(phase=3, key="auto_excluded",
           value={"count": N, "top_reasons": [{"reason": "...", "n": N}, ...]},
           rationale="High-confidence exclusions", confidence="auto")
logger.log(phase=3, key="auto_included",
           value={"count": N, "pmids": [...]},
           rationale="High-confidence inclusions", confidence="auto")
logger.log(phase=3, key="uncertain_decisions",
           value=[{"pmid": "...", "title": "...", "decision": "include/exclude", "reason": "..."}],
           rationale="Best-guess decisions for ambiguous papers",
           confidence="needs_review")
```

Build `prisma_data.json` with flow counts.

**Tip:** For >200 records, screen in batches of 50. Auto-exclude obvious mismatches first
to narrow the pool quickly.

**Output:** `screening_results.json`, `prisma_data.json`

---

### Phase 4: Data Extraction

**Goal:** Extract quantitative and qualitative data from each included study, with drug
stratification for pharmacological reviews.

#### Determine effect measure

Scan all included studies (using full text from `fulltext_data/` where available) and produce
an **effect measure frequency summary**:

```
Effect measure reporting across included studies:
  OR (odds ratio): 7 studies — reported directly
  Raw events (convertible to OR/RR): 5 studies — event counts in results tables
  HR (hazard ratio): 2 studies — Cox regression results
  Adjusted OR: 3 studies — from multivariate logistic regression
```

Choose the most appropriate effect measure based on frequency and outcome type. Log the
frequency summary and choice:

```python
logger.log(phase=4, key="effect_measure_frequency",
           value={"OR": 7, "raw_events": 5, "HR": 2, "adjusted_OR": 3},
           rationale="Surveyed all included studies' results sections and tables",
           confidence="auto")
logger.log(phase=4, key="effect_measure_chosen",
           value="OR",
           rationale="Binary outcome (HF hospitalization). 7/12 studies report OR natively. "
                     "5 more have raw events convertible to OR. HR studies excluded from primary "
                     "analysis (addressed in sensitivity analysis).",
           confidence="auto")
```

#### Drug stratification (pharmacological reviews)

When the review involves a drug class (identifiable by ATC code or user mention of a class
name like "SGLT2 inhibitors", "statins", "ACE inhibitors"), automatically:

1. Identify each individual drug and dose tested across all included studies
2. Produce a **stratification summary**:

```
Drug stratification:
  Empagliflozin 10mg: 4 studies, N=12,450
  Empagliflozin 25mg: 2 studies, N=6,200
  Dapagliflozin 10mg: 3 studies, N=8,200
  Canagliflozin 300mg: 2 studies, N=4,100
  Mixed/class-level (no specific drug): 3 studies, N=6,800
```

3. Decide on stratification approach. Prefer individual drug analysis when ≥2 studies per
   drug exist. Studies reporting class-level results go into a separate subgroup.

```python
logger.log(phase=4, key="drug_stratification",
           value={"drugs": [...], "approach": "individual_drug", "class_level_studies": [...]},
           rationale="Sufficient per-drug studies for individual pooling. Class-level studies "
                     "kept as separate subgroup.",
           confidence="auto")
```

#### Extract data

For each included study, extract data from full-text tables (not just abstracts). Use
`fulltext_data/<pmid>.json` for structured table access. For each extracted value, record
the source:

Extract into `extracted_data.csv` (columns per effect measure — see
`references/extraction_templates.md`) with additional columns:
- `drug`: specific drug name (for pharmacological reviews)
- `dose`: dose tested
- `source_table`: which table the data came from (e.g., "Table 2, row 3")
- `source_notes`: any conversions applied (e.g., "SE converted to SD: SD = SE × √n")

Extract study characteristics into `study_characteristics.csv` (see
`references/extraction_templates.md` for columns).

Assess risk of bias:
- RCTs: Cochrane RoB 2 (5 domains → Low / Some concerns / High)
- Observational: Newcastle-Ottawa Scale (0–9 stars)

Log extraction decisions:
```python
logger.log(phase=4, key="data_extraction_summary",
           value={"studies_extracted": N, "conversions_applied": [...],
                  "data_source_tracking": [{"study": "Smith 2020", "table": "Table 2", "values": {...}}]},
           rationale="Extracted from full-text tables where available, abstract for PMIDs without PMC access",
           confidence="auto")
```

**Output:** `extracted_data.csv`, `study_characteristics.csv`

---

### Phase 5: Meta-Analysis

**Goal:** Pool effect estimates, quantify heterogeneity, assess publication bias.

#### Run meta-analysis

If drug stratification is active, run separately for each drug subgroup AND for the
overall class:

```bash
# Overall
python $SKILL_DIR/scripts/meta_analysis.py extracted_data.csv \
  --measure OR --output meta_results.json

# Per-drug (filter CSV to each drug first)
python $SKILL_DIR/scripts/meta_analysis.py extracted_data_empagliflozin.csv \
  --measure OR --output meta_results_empagliflozin.json
```

#### Generate figures

```bash
python $SKILL_DIR/scripts/generate_figures.py meta_results.json \
  --forest forest_plot.png --funnel funnel_plot.png \
  --prisma prisma_data.json --prisma-out prisma_diagram.png \
  --title "<Review Title>"
```

Generate per-drug forest plots if stratified.

#### Automatic sensitivity analyses

Run these automatically:
1. **Exclude high-RoB studies** — rerun without studies scored High on risk of bias
2. **Subgroup by drug** (if pharmacological) — compare pooled effects across drugs
3. **If I² > 75%** — explore subgroups by study design, population, or follow-up duration

Log results:
```python
logger.log(phase=5, key="primary_analysis",
           value={"pooled_effect": 0.72, "ci": [0.61, 0.85], "I2": 42.1, "k": 12},
           rationale="DerSimonian-Laird random effects", confidence="auto")
logger.log(phase=5, key="sensitivity_exclude_high_rob",
           value={"pooled_effect": 0.71, "ci": [0.59, 0.86], "k": 10,
                  "interpretation": "Direction and significance unchanged"},
           rationale="Removed 2 high-RoB studies", confidence="auto")
```

**If k < 3 studies:** Do not pool. Perform narrative synthesis only. Log this decision.

**Output:** `meta_results.json`, `forest_plot.png`, `funnel_plot.png`, `prisma_diagram.png`

---

### Phase 6: Report & Decision Review

**Goal:** Generate the full report and append the decision review section.

1. Create `systematic_review_report.md` following the standard PRISMA structure
   (see the report template in `references/extraction_templates.md` — sections: Executive
   Summary, Background, Methods, Results, Discussion, Conclusion, Included Studies).

2. Include GRADE assessment for each primary outcome.

3. Save the decision log:
   ```python
   logger.save()
   ```

4. Generate the draft review with checkpoints:
   ```bash
   python $SKILL_DIR/scripts/generate_review_report.py \
     --decisions decisions_log.json \
     --report systematic_review_report.md \
     --output draft_review.md
   ```

5. Present `draft_review.md` to the user and explain:
   - Pre-checked items (✓) are decisions Claude is confident about — skim and move on
   - Unchecked items (☐) need their attention
   - "Change to" fields are where they write overrides
   - When done reviewing, tell Claude to finalize or rerun

**Output:** `systematic_review_report.md`, `decisions_log.json`, `draft_review.md`

---

## Stage 2: Review & Rerun

When the user submits their reviewed `draft_review.md` with changes:

1. Parse the user's modifications to identify changed decisions.

2. Determine rerun scope:
   ```bash
   python $SKILL_DIR/scripts/rerun_from_changes.py \
     --original decisions_log.json \
     --modified decisions_modified.json
   ```

3. Rerun only affected phases (from earliest change through Phase 6).

4. Regenerate `draft_review.md` with updated decisions and results.

5. If no changes were made, finalize the report as-is.

**Rerun examples:**
- Change PICO → rerun phases 1-6
- Change screening decision → rerun phases 3-6
- Change drug stratification → rerun phases 5-6
- Change nothing → finalize report

---

## Phase Summary

| Phase | Key files | Decision logging |
|-------|-----------|-----------------|
| 1. Topic refinement | `pico.md` | PICO, search string, design filter |
| 2. Literature search | `pubmed_results.json`, `fulltext_data/`, `search_log.md` | Query, result count, no-fulltext PMIDs |
| 3. Screening | `screening_results.json`, `prisma_data.json` | Auto-exclude/include/uncertain counts |
| 4. Data extraction | `extracted_data.csv`, `study_characteristics.csv` | Effect measure, drug stratification, source tracking |
| 5. Meta-analysis | `meta_results.json`, PNG figures | Pooled results, sensitivity analyses |
| 6. Report | `draft_review.md`, `decisions_log.json` | All above consolidated |

For statistical method details: `references/statistics_guide.md`
For extraction column definitions: `references/extraction_templates.md`
