# Autonomous Systematic Review Redesign

**Date:** 2026-03-09

## Problem

The current systematic review skill is too manually intensive and extractions are not precise enough:

1. **Screening is tedious** — Claude asks the user to manually confirm every paper one-by-one, even papers it already flagged as ineligible.
2. **Shallow extraction** — Claude only uses abstracts, not full-text tables where actual numeric data lives.
3. **Over-aggregation** — for pharmacological reviews, Claude pools an entire drug class together instead of stratifying by individual drug/dose.
4. **Too many checkpoints** — 6 user checkpoints create excessive back-and-forth.
5. **Effect measure reporting not summarized** — Claude picks an effect measure without showing the user how each study actually reports its data.

## Design: Two-Stage Autonomous Review

### Stage 1 — Autonomous Run

Claude executes all 6 phases without stopping. Every decision that would normally require user input is logged to `decisions_log.json` with rationale and confidence level.

#### Phase 1: Topic Refinement
- Claude structures PICO from the user's prompt, picks MeSH terms, builds the search string.
- Logged decisions: PICO choices, MeSH terms, search string, study design filter.

#### Phase 2: PubMed Search + PMC Full-Text Fetch
- Runs `pubmed_search.py`, then `pmc_fulltext.py` to fetch full-text XML from PMC for every included result.
- Logged decisions: search string used, result count, papers without PMC full text (flagged for manual sourcing).

#### Phase 3: Screening
- Confidence-tier system:
  - **Auto-exclude** (high confidence fail) — logged with reason, no user review needed unless overridden.
  - **Auto-include** (high confidence match) — logged with reason.
  - **Uncertain** — Claude makes best-guess decision, logged with what was ambiguous.
- For papers with PMC full text, Claude uses full text to resolve uncertainty.
- Logged decisions: every include/exclude/uncertain decision with reason, PRISMA flow counts.

#### Phase 4: Data Extraction
- Claude reads all tables from full-text papers (not just abstracts).
- Produces an **effect measure frequency summary** (e.g., "7 studies report OR, 3 report HR").
- For pharmacological reviews: auto-detects individual drugs/doses within the class using ATC codes.
- Produces a **stratification summary** (drug x dose x study count x total N).
- Logged decisions: effect measure chosen and why, stratification approach, data source tracing (paper -> table -> cell), any conversions applied (SE->SD, etc.).

#### Phase 5: Meta-Analysis
- Runs `meta_analysis.py` and `generate_figures.py`.
- If I² > 75%, automatically runs sensitivity analyses (exclude high-RoB, subgroup by drug).
- Logged decisions: model chosen, sensitivity analyses run, heterogeneity interpretation.

#### Phase 6: Report Generation
- Generates `systematic_review_report.md` plus all figures.
- Appends the Decision Review Section (see Stage 2).

### Stage 2 — Review & Rerun

Claude generates a draft report with all logged decisions embedded as reviewable checkpoints:

- **Pre-checked boxes** = Claude is confident (user skims and moves on).
- **Unchecked boxes** = Claude wants user attention (e.g., papers without full text, uncertain screening decisions).
- **"Change to" fields** = where user writes overrides.
- Every data point links back to its source (paper, table, cell).

Decisions are grouped by phase. When the user submits changes, Claude diffs against original decisions and reruns only phases downstream of the earliest change.

### Decision Review Format

```markdown
## Decision Review

### Phase 1: Topic Refinement
- [x] **PICO Definition**
  Population: ... | Intervention: ... | Comparison: ... | Outcome: ...
  _Rationale: ..._
  → Change to: ___

- [x] **Search String**
  `(...)`
  → Change to: ___

### Phase 2: Literature Search
- [x] **Max results: 500**
- [ ] **N papers without PMC full text** (see list)
  → Papers: [PMID list with titles]

### Phase 3: Screening
- [x] **Auto-excluded: N papers** ([view list](screening_results.json))
  → Override any? List PMIDs: ___
- [x] **Auto-included: N papers**
  → Remove any? List PMIDs: ___
- [x] **Uncertain: N papers** — Claude's best guess applied:
  [table of uncertain decisions]
  → Change any? ___

### Phase 4: Data Extraction
- [x] **Effect measure: [chosen]**
  _Frequency summary: OR ×N, HR ×N, RR ×N_
  → Change to: ___
- [x] **Drug stratification: [approach]**
  [drug x dose x studies x N table]
  → Pool differently? ___
- [x] **Data source tracking** ([view table](extracted_data.csv))
  → Flag values to re-check? ___

### Phase 5: Meta-Analysis
- [x] **Model: Random-effects (DerSimonian-Laird)**
- [x] **Sensitivity analysis: [description]**
- [x] **Heterogeneity: I²=N%**
  → Request additional subgroup analyses? ___
```

## New Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `pmc_fulltext.py` | Fetch full-text XML from PMC, extract structured tables | `pubmed_results.json` or PMID list | `fulltext_data/` directory (one JSON per paper) + `no_fulltext.json` |
| `decisions_logger.py` | Accumulate decisions across phases | Append calls: phase, key, value, rationale, confidence | `decisions_log.json` |
| `generate_review_report.py` | Combine report + decisions into reviewable draft | `decisions_log.json`, `systematic_review_report.md`, screening/extraction data | `draft_review.md` |
| `rerun_from_changes.py` | Parse user modifications, determine rerun scope | Original + modified `decisions_log.json` | List of phases to rerun + updated parameters |

Existing scripts (`pubmed_search.py`, `meta_analysis.py`, `generate_figures.py`) remain unchanged.

## SKILL.md Changes

The SKILL.md will be rewritten to reflect the two-stage architecture:
- Remove per-phase user checkpoints
- Add Stage 1 instructions (autonomous run with decision logging)
- Add Stage 2 instructions (review format, rerun logic)
- Add pharmacological review guidance (drug stratification, ATC code detection)
- Add full-text extraction guidance (PMC fetching, table parsing)

## Rerun Logic

When the user submits changes:
1. Diff modified decisions against original `decisions_log.json`.
2. Identify the earliest phase with a change.
3. Rerun that phase and all downstream phases with updated parameters.
4. Regenerate report and decision review section.

Examples:
- Change PICO → rerun phases 1-6
- Change screening decision → rerun phases 3-6
- Change drug stratification only → rerun phases 5-6
- Change nothing → finalize report as-is
