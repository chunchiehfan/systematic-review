# Autonomous Systematic Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the systematic-review skill from a 6-checkpoint manual workflow into a two-stage autonomous system: Claude runs the full review unattended, then presents a single consolidated decision review for user approval.

**Architecture:** Stage 1 runs phases 1-6 autonomously, logging every decision to `decisions_log.json`. Stage 2 generates a draft report with embedded checkpoints the user reviews in one pass. On user submission, only phases downstream of changes are rerun. A new `pmc_fulltext.py` script fetches full-text from PubMed Central. Drug stratification is built into the extraction phase.

**Tech Stack:** Python 3 (stdlib + urllib for NCBI APIs), matplotlib/scipy/numpy (existing), JSON/CSV for data interchange.

---

### Task 1: `decisions_logger.py` — Decision Logging Utility

This is a dependency for all other tasks, so build it first.

**Files:**
- Create: `scripts/decisions_logger.py`
- Test: `scripts/test_decisions_logger.py`

**Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for decisions_logger.py"""
import json
import os
import tempfile
import unittest

from decisions_logger import DecisionLogger


class TestDecisionLogger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmpdir, "decisions_log.json")
        self.logger = DecisionLogger(self.log_path)

    def test_log_single_decision(self):
        self.logger.log(
            phase=1,
            key="pico_definition",
            value={"P": "Adults with T2DM", "I": "SGLT2i", "C": "Placebo", "O": "HF hospitalization"},
            rationale="Derived from user prompt",
            confidence="auto",
        )
        self.logger.save()
        with open(self.log_path) as f:
            data = json.load(f)
        self.assertEqual(len(data["decisions"]), 1)
        self.assertEqual(data["decisions"][0]["phase"], 1)
        self.assertEqual(data["decisions"][0]["key"], "pico_definition")
        self.assertEqual(data["decisions"][0]["confidence"], "auto")

    def test_log_multiple_decisions_across_phases(self):
        self.logger.log(phase=1, key="pico", value="test", rationale="r1", confidence="auto")
        self.logger.log(phase=3, key="screening", value="test2", rationale="r2", confidence="needs_review")
        self.logger.save()
        with open(self.log_path) as f:
            data = json.load(f)
        self.assertEqual(len(data["decisions"]), 2)
        self.assertEqual(data["decisions"][1]["confidence"], "needs_review")

    def test_get_decisions_by_phase(self):
        self.logger.log(phase=1, key="a", value="1", rationale="", confidence="auto")
        self.logger.log(phase=2, key="b", value="2", rationale="", confidence="auto")
        self.logger.log(phase=1, key="c", value="3", rationale="", confidence="auto")
        phase1 = self.logger.get_by_phase(1)
        self.assertEqual(len(phase1), 2)

    def test_load_existing_log(self):
        self.logger.log(phase=1, key="a", value="1", rationale="", confidence="auto")
        self.logger.save()
        logger2 = DecisionLogger(self.log_path)
        self.assertEqual(len(logger2.decisions), 1)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_decisions_logger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'decisions_logger'`

**Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Decision logging utility for autonomous systematic review.

Accumulates decisions across phases so they can be rendered as
reviewable checkpoints in the final draft report.

Usage:
    from decisions_logger import DecisionLogger
    logger = DecisionLogger("decisions_log.json")
    logger.log(phase=1, key="pico_definition", value={...}, rationale="...", confidence="auto")
    logger.save()
"""
import json
from pathlib import Path


class DecisionLogger:
    def __init__(self, output_path: str = "decisions_log.json"):
        self.output_path = Path(output_path)
        self.decisions = []
        if self.output_path.exists():
            with open(self.output_path) as f:
                data = json.load(f)
            self.decisions = data.get("decisions", [])

    def log(self, phase: int, key: str, value, rationale: str, confidence: str):
        """
        Log a decision.

        Args:
            phase: Phase number (1-6)
            key: Decision identifier (e.g., "pico_definition", "search_string")
            value: The decision value (any JSON-serializable type)
            rationale: Why this decision was made
            confidence: "auto" (pre-checked, Claude confident) or "needs_review" (unchecked, user should look)
        """
        self.decisions.append({
            "phase": phase,
            "key": key,
            "value": value,
            "rationale": rationale,
            "confidence": confidence,
        })

    def get_by_phase(self, phase: int) -> list:
        return [d for d in self.decisions if d["phase"] == phase]

    def save(self):
        self.output_path.write_text(json.dumps({"decisions": self.decisions}, indent=2, ensure_ascii=False))

    def to_dict(self) -> dict:
        return {"decisions": self.decisions}
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_decisions_logger.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add scripts/decisions_logger.py scripts/test_decisions_logger.py
git commit -m "feat: add decision logging utility for autonomous review"
```

---

### Task 2: `pmc_fulltext.py` — PMC Full-Text Fetcher

Fetches full-text XML from PubMed Central and extracts structured tables.

**Files:**
- Create: `scripts/pmc_fulltext.py`
- Test: `scripts/test_pmc_fulltext.py`

**Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for pmc_fulltext.py — uses mocked HTTP responses."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pmc_fulltext import (
    pmid_to_pmcid,
    fetch_pmc_xml,
    extract_tables_from_xml,
    parse_table_element,
)


SAMPLE_ID_CONVERTER_RESPONSE = json.dumps({
    "records": [
        {"pmid": "12345678", "pmcid": "PMC7654321"},
        {"pmid": "87654321", "errmsg": "not found"},
    ]
})

SAMPLE_PMC_XML = """<?xml version="1.0"?>
<pmc-articleset>
<article>
<body>
<sec><title>Results</title>
<p>The primary outcome occurred in 45 of 230 patients (19.6%) in the treatment group
and 67 of 225 (29.8%) in the control group.</p>
<table-wrap id="tab1">
<label>Table 1</label>
<caption><title>Baseline characteristics</title></caption>
<table>
<thead><tr><th>Variable</th><th>Treatment (n=230)</th><th>Control (n=225)</th></tr></thead>
<tbody>
<tr><td>Age, mean (SD)</td><td>62.3 (11.2)</td><td>63.1 (10.8)</td></tr>
<tr><td>Male, n (%)</td><td>142 (61.7)</td><td>138 (61.3)</td></tr>
</tbody>
</table>
</table-wrap>
</sec>
</body>
</article>
</pmc-articleset>"""


class TestPmidToPmcid(unittest.TestCase):
    @patch("pmc_fulltext.urllib.request.urlopen")
    def test_converts_pmids(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_ID_CONVERTER_RESPONSE.encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = pmid_to_pmcid(["12345678", "87654321"])
        self.assertEqual(result["12345678"], "PMC7654321")
        self.assertNotIn("87654321", result)


class TestExtractTables(unittest.TestCase):
    def test_extract_tables_from_xml(self):
        tables = extract_tables_from_xml(SAMPLE_PMC_XML)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["label"], "Table 1")
        self.assertEqual(tables[0]["caption"], "Baseline characteristics")
        self.assertEqual(len(tables[0]["rows"]), 2)
        self.assertEqual(tables[0]["headers"], ["Variable", "Treatment (n=230)", "Control (n=225)"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_pmc_fulltext.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pmc_fulltext'`

**Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Fetch full-text articles from PubMed Central and extract structured tables.

Uses NCBI ID Converter API to map PMIDs → PMCIDs, then efetch for full-text XML.
Extracts all <table-wrap> elements into structured JSON.

Usage:
    python pmc_fulltext.py pubmed_results.json --output-dir fulltext_data/ --api-key KEY
    python pmc_fulltext.py --pmids 12345678 87654321 --output-dir fulltext_data/
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def pmid_to_pmcid(pmids: list[str], api_key: str = None) -> dict[str, str]:
    """Convert PMIDs to PMCIDs using NCBI ID Converter. Returns {pmid: pmcid} for found entries."""
    mapping = {}
    batch_size = 200
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        params = {
            "ids": ",".join(batch),
            "format": "json",
            "tool": "systematic-review-skill",
            "email": "systematic-review@example.com",
        }
        if api_key:
            params["api_key"] = api_key
        url = f"{CONVERTER_URL}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read())
            for record in data.get("records", []):
                pmcid = record.get("pmcid")
                pmid = record.get("pmid")
                if pmcid and pmid:
                    mapping[pmid] = pmcid
        except urllib.error.URLError as e:
            print(f"  Warning: ID converter batch failed: {e}", file=sys.stderr)
        time.sleep(0.35 if not api_key else 0.1)
    return mapping


def fetch_pmc_xml(pmcid: str, api_key: str = None) -> str:
    """Fetch full-text XML for a single PMC article."""
    params = {
        "db": "pmc",
        "id": pmcid,
        "rettype": "full",
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{EFETCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"  Warning: Failed to fetch {pmcid}: {e}", file=sys.stderr)
        return ""


def parse_table_element(table_wrap: ET.Element) -> dict:
    """Parse a <table-wrap> element into structured data."""
    label_el = table_wrap.find("label")
    label = label_el.text.strip() if label_el is not None and label_el.text else ""

    caption_el = table_wrap.find(".//caption/title")
    if caption_el is None:
        caption_el = table_wrap.find(".//caption")
    caption = "".join(caption_el.itertext()).strip() if caption_el is not None else ""

    table_el = table_wrap.find(".//table")
    if table_el is None:
        return {"label": label, "caption": caption, "headers": [], "rows": []}

    headers = []
    thead = table_el.find("thead")
    if thead is not None:
        for th in thead.findall(".//th"):
            headers.append("".join(th.itertext()).strip())
        if not headers:
            first_row = thead.find("tr")
            if first_row is not None:
                for td in first_row.findall("td"):
                    headers.append("".join(td.itertext()).strip())

    rows = []
    tbody = table_el.find("tbody")
    row_elements = tbody.findall("tr") if tbody is not None else table_el.findall("tr")
    for tr in row_elements:
        cells = []
        for cell in tr.findall("td"):
            cells.append("".join(cell.itertext()).strip())
        if not cells:
            for cell in tr.findall("th"):
                cells.append("".join(cell.itertext()).strip())
        if cells:
            rows.append(cells)

    return {"label": label, "caption": caption, "headers": headers, "rows": rows}


def extract_tables_from_xml(xml_text: str) -> list[dict]:
    """Extract all tables from a PMC full-text XML string."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    tables = []
    for table_wrap in root.findall(".//table-wrap"):
        parsed = parse_table_element(table_wrap)
        tables.append(parsed)
    return tables


def extract_sections_text(xml_text: str) -> list[dict]:
    """Extract section titles and text from PMC XML body."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    sections = []
    for sec in root.findall(".//body//sec"):
        title_el = sec.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        paragraphs = []
        for p in sec.findall("p"):
            text = "".join(p.itertext()).strip()
            if text:
                paragraphs.append(text)
        if title or paragraphs:
            sections.append({"title": title, "text": "\n".join(paragraphs)})
    return sections


def process_articles(pmids: list[str], output_dir: Path, api_key: str = None) -> dict:
    """
    Fetch full text for a list of PMIDs and save structured data.
    Returns summary: {fetched: [...], no_fulltext: [...]}.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting {len(pmids)} PMIDs to PMCIDs...")
    pmcid_map = pmid_to_pmcid(pmids, api_key)
    print(f"  Found {len(pmcid_map)} articles in PMC out of {len(pmids)}")

    fetched = []
    no_fulltext = []
    delay = 0.1 if api_key else 0.35

    for pmid in pmids:
        pmcid = pmcid_map.get(pmid)
        if not pmcid:
            no_fulltext.append(pmid)
            continue

        print(f"  Fetching {pmcid} (PMID: {pmid})...", end="\r")
        xml_text = fetch_pmc_xml(pmcid, api_key)
        if not xml_text:
            no_fulltext.append(pmid)
            continue

        tables = extract_tables_from_xml(xml_text)
        sections = extract_sections_text(xml_text)

        article_data = {
            "pmid": pmid,
            "pmcid": pmcid,
            "tables": tables,
            "sections": sections,
        }

        out_file = output_dir / f"{pmid}.json"
        out_file.write_text(json.dumps(article_data, indent=2, ensure_ascii=False))
        fetched.append(pmid)
        time.sleep(delay)

    print(f"\nFetched full text for {len(fetched)} articles. {len(no_fulltext)} not available in PMC.")
    return {"fetched": fetched, "no_fulltext": no_fulltext}


def main():
    parser = argparse.ArgumentParser(
        description="Fetch PMC full-text articles and extract structured tables.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("input_json", nargs="?", help="pubmed_results.json or screening_results.json")
    group.add_argument("--pmids", nargs="+", help="Space-separated PMIDs")
    parser.add_argument("--output-dir", default="fulltext_data", help="Output directory (default: fulltext_data/)")
    parser.add_argument("--api-key", help="NCBI API key")
    args = parser.parse_args()

    if args.pmids:
        pmids = args.pmids
    else:
        input_path = Path(args.input_json)
        if not input_path.exists():
            print(f"Error: {input_path} not found.", file=sys.stderr)
            sys.exit(1)
        with open(input_path) as f:
            data = json.load(f)
        if isinstance(data, list):
            pmids = [str(item.get("pmid", "")) for item in data if item.get("pmid")]
        else:
            pmids = data.get("pmids", [])

    output_dir = Path(args.output_dir)
    summary = process_articles(pmids, output_dir, args.api_key)

    no_ft_path = output_dir / "no_fulltext.json"
    no_ft_path.write_text(json.dumps(summary["no_fulltext"], indent=2))
    print(f"No-fulltext PMIDs saved to {no_ft_path}")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_pmc_fulltext.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add scripts/pmc_fulltext.py scripts/test_pmc_fulltext.py
git commit -m "feat: add PMC full-text fetcher with table extraction"
```

---

### Task 3: `generate_review_report.py` — Decision Review Report Generator

Takes `decisions_log.json` and the draft report, produces the reviewable `draft_review.md` with checkpoint format.

**Files:**
- Create: `scripts/generate_review_report.py`
- Test: `scripts/test_generate_review_report.py`

**Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for generate_review_report.py"""
import json
import os
import tempfile
import unittest

from generate_review_report import render_decision_review


class TestRenderDecisionReview(unittest.TestCase):
    def test_auto_decisions_are_prechecked(self):
        decisions = {
            "decisions": [
                {"phase": 1, "key": "pico_definition", "value": "test", "rationale": "reason", "confidence": "auto"},
            ]
        }
        md = render_decision_review(decisions)
        self.assertIn("- [x]", md)
        self.assertIn("pico_definition", md)

    def test_needs_review_decisions_are_unchecked(self):
        decisions = {
            "decisions": [
                {"phase": 2, "key": "no_fulltext_papers", "value": ["123", "456"], "rationale": "not in PMC", "confidence": "needs_review"},
            ]
        }
        md = render_decision_review(decisions)
        self.assertIn("- [ ]", md)

    def test_decisions_grouped_by_phase(self):
        decisions = {
            "decisions": [
                {"phase": 1, "key": "a", "value": "1", "rationale": "", "confidence": "auto"},
                {"phase": 3, "key": "b", "value": "2", "rationale": "", "confidence": "auto"},
                {"phase": 1, "key": "c", "value": "3", "rationale": "", "confidence": "auto"},
            ]
        }
        md = render_decision_review(decisions)
        self.assertIn("### Phase 1:", md)
        self.assertIn("### Phase 3:", md)

    def test_change_to_field_present(self):
        decisions = {
            "decisions": [
                {"phase": 1, "key": "search_string", "value": "(test query)", "rationale": "built from PICO", "confidence": "auto"},
            ]
        }
        md = render_decision_review(decisions)
        self.assertIn("Change to:", md)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_generate_review_report.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Generate a draft review report with embedded decision checkpoints.

Reads decisions_log.json and the draft systematic_review_report.md,
produces draft_review.md with the Decision Review Section appended.

Usage:
    python generate_review_report.py \
        --decisions decisions_log.json \
        --report systematic_review_report.md \
        --output draft_review.md
"""
import argparse
import json
import sys
from pathlib import Path

PHASE_NAMES = {
    1: "Topic Refinement",
    2: "Literature Search",
    3: "Screening",
    4: "Data Extraction",
    5: "Meta-Analysis",
    6: "Report Generation",
}


def format_value(value) -> str:
    """Format a decision value for display in markdown."""
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(f"{k}: {v}")
        return " | ".join(parts)
    if isinstance(value, list):
        if len(value) <= 5:
            return ", ".join(str(v) for v in value)
        return f"{', '.join(str(v) for v in value[:5])}... ({len(value)} total)"
    return str(value)


def format_key(key: str) -> str:
    """Convert snake_case key to Title Case display name."""
    return key.replace("_", " ").title()


def render_decision_review(decisions_data: dict) -> str:
    """Render the Decision Review Section as markdown."""
    decisions = decisions_data.get("decisions", [])
    if not decisions:
        return "## Decision Review\n\nNo decisions were logged.\n"

    # Group by phase
    by_phase = {}
    for d in decisions:
        phase = d["phase"]
        if phase not in by_phase:
            by_phase[phase] = []
        by_phase[phase].append(d)

    lines = ["## Decision Review\n"]

    for phase in sorted(by_phase.keys()):
        phase_name = PHASE_NAMES.get(phase, f"Phase {phase}")
        lines.append(f"### Phase {phase}: {phase_name}\n")

        for d in by_phase[phase]:
            checkbox = "[x]" if d["confidence"] == "auto" else "[ ]"
            key_display = format_key(d["key"])
            value_display = format_value(d["value"])

            lines.append(f"- {checkbox} **{key_display}**")
            lines.append(f"  {value_display}")
            if d.get("rationale"):
                lines.append(f"  _Rationale: {d['rationale']}_")
            lines.append(f"  → Change to: ___\n")

    return "\n".join(lines)


def generate_draft_review(decisions_path: str, report_path: str, output_path: str):
    """Combine the report and decision review into a single draft."""
    with open(decisions_path) as f:
        decisions_data = json.load(f)

    report_text = ""
    report_file = Path(report_path)
    if report_file.exists():
        report_text = report_file.read_text()

    review_section = render_decision_review(decisions_data)

    draft = f"{report_text}\n\n---\n\n{review_section}"

    Path(output_path).write_text(draft)
    print(f"Draft review saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate draft review report with decision checkpoints.")
    parser.add_argument("--decisions", required=True, help="Path to decisions_log.json")
    parser.add_argument("--report", required=True, help="Path to systematic_review_report.md")
    parser.add_argument("--output", default="draft_review.md", help="Output path (default: draft_review.md)")
    args = parser.parse_args()

    generate_draft_review(args.decisions, args.report, args.output)


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_generate_review_report.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add scripts/generate_review_report.py scripts/test_generate_review_report.py
git commit -m "feat: add decision review report generator"
```

---

### Task 4: `rerun_from_changes.py` — Change Detection and Rerun Logic

Parses user modifications to the decision log and determines which phases need rerunning.

**Files:**
- Create: `scripts/rerun_from_changes.py`
- Test: `scripts/test_rerun_from_changes.py`

**Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for rerun_from_changes.py"""
import unittest

from rerun_from_changes import diff_decisions, phases_to_rerun


class TestDiffDecisions(unittest.TestCase):
    def test_no_changes(self):
        original = [{"phase": 1, "key": "pico", "value": "A", "rationale": "", "confidence": "auto"}]
        modified = [{"phase": 1, "key": "pico", "value": "A", "rationale": "", "confidence": "auto"}]
        diffs = diff_decisions(original, modified)
        self.assertEqual(len(diffs), 0)

    def test_value_changed(self):
        original = [{"phase": 3, "key": "screening", "value": "include", "rationale": "", "confidence": "auto"}]
        modified = [{"phase": 3, "key": "screening", "value": "exclude", "rationale": "", "confidence": "auto"}]
        diffs = diff_decisions(original, modified)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["phase"], 3)

    def test_multiple_changes_different_phases(self):
        original = [
            {"phase": 1, "key": "pico", "value": "A", "rationale": "", "confidence": "auto"},
            {"phase": 4, "key": "measure", "value": "OR", "rationale": "", "confidence": "auto"},
        ]
        modified = [
            {"phase": 1, "key": "pico", "value": "B", "rationale": "", "confidence": "auto"},
            {"phase": 4, "key": "measure", "value": "RR", "rationale": "", "confidence": "auto"},
        ]
        diffs = diff_decisions(original, modified)
        self.assertEqual(len(diffs), 2)


class TestPhasesToRerun(unittest.TestCase):
    def test_change_in_phase_1_reruns_all(self):
        diffs = [{"phase": 1, "key": "pico", "old": "A", "new": "B"}]
        result = phases_to_rerun(diffs)
        self.assertEqual(result, [1, 2, 3, 4, 5, 6])

    def test_change_in_phase_4_reruns_4_through_6(self):
        diffs = [{"phase": 4, "key": "measure", "old": "OR", "new": "RR"}]
        result = phases_to_rerun(diffs)
        self.assertEqual(result, [4, 5, 6])

    def test_no_changes_empty_rerun(self):
        result = phases_to_rerun([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_rerun_from_changes.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Detect changes between original and modified decision logs.
Determines which phases need to be rerun.

Usage:
    python rerun_from_changes.py --original decisions_log.json --modified decisions_modified.json
"""
import argparse
import json
import sys
from pathlib import Path


def diff_decisions(original: list[dict], modified: list[dict]) -> list[dict]:
    """
    Compare original and modified decision lists.
    Returns list of diffs: [{phase, key, old, new}, ...]
    Matches decisions by index position (same order assumed).
    """
    diffs = []
    for i, (orig, mod) in enumerate(zip(original, modified)):
        if orig.get("value") != mod.get("value"):
            diffs.append({
                "phase": orig["phase"],
                "key": orig["key"],
                "old": orig.get("value"),
                "new": mod.get("value"),
            })
    return diffs


def phases_to_rerun(diffs: list[dict]) -> list[int]:
    """
    Given a list of diffs, return sorted list of phases that need rerunning.
    All phases from the earliest changed phase through phase 6 are rerun.
    """
    if not diffs:
        return []
    earliest = min(d["phase"] for d in diffs)
    return list(range(earliest, 7))


def main():
    parser = argparse.ArgumentParser(description="Detect decision changes and determine rerun scope.")
    parser.add_argument("--original", required=True, help="Original decisions_log.json")
    parser.add_argument("--modified", required=True, help="Modified decisions_log.json")
    args = parser.parse_args()

    orig_path = Path(args.original)
    mod_path = Path(args.modified)

    if not orig_path.exists() or not mod_path.exists():
        print("Error: both files must exist.", file=sys.stderr)
        sys.exit(1)

    with open(orig_path) as f:
        original = json.load(f).get("decisions", [])
    with open(mod_path) as f:
        modified = json.load(f).get("decisions", [])

    diffs = diff_decisions(original, modified)
    rerun = phases_to_rerun(diffs)

    result = {"diffs": diffs, "phases_to_rerun": rerun}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `cd ~/.claude/skills/systematic-review/scripts && python -m pytest test_rerun_from_changes.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add scripts/rerun_from_changes.py scripts/test_rerun_from_changes.py
git commit -m "feat: add change detection and rerun logic"
```

---

### Task 5: Rewrite SKILL.md — Two-Stage Autonomous Architecture

This is the main skill rewrite. Replace the current 6-checkpoint workflow with the autonomous two-stage design.

**Files:**
- Modify: `SKILL.md`

**Step 1: Read the current SKILL.md**

Run: Read `~/.claude/skills/systematic-review/SKILL.md` to confirm current state.

**Step 2: Rewrite SKILL.md**

Replace the entire SKILL.md with the new two-stage autonomous architecture. The new version should:

- Keep the same YAML frontmatter `name` but update the `description` to mention autonomous operation
- Replace the 6 per-phase checkpoints with Stage 1 (autonomous) and Stage 2 (review)
- Add PMC full-text fetching instructions in Phase 2
- Add confidence-tier screening in Phase 3
- Add drug stratification and effect measure frequency summary in Phase 4
- Add automatic sensitivity analysis in Phase 5
- Add decision review generation in Phase 6
- Add Stage 2 instructions for interpreting user feedback and rerunning
- Reference all new scripts with `$SKILL_DIR/scripts/` paths
- Keep references to existing `references/statistics_guide.md` and `references/extraction_templates.md`

The full rewritten SKILL.md content:

````markdown
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
````

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "feat: rewrite SKILL.md for autonomous two-stage review architecture"
```

---

### Task 6: Update `evals/evals.json` for New Workflow

Update the test cases to reflect the autonomous workflow expectations.

**Files:**
- Modify: `evals/evals.json`

**Step 1: Rewrite evals.json**

```json
{
  "skill_name": "systematic-review",
  "evals": [
    {
      "id": 1,
      "prompt": "I want to do a systematic review on the effectiveness of SGLT2 inhibitors in reducing hospitalization for heart failure in patients with type 2 diabetes. Can you help me get started?",
      "expected_output": "Skill should run all 6 phases autonomously: (1) define PICO, (2) run PubMed search + PMC full-text fetch, (3) screen with confidence tiers, (4) extract data with drug stratification (empagliflozin/dapagliflozin/canagliflozin), (5) run meta-analysis with per-drug subgroups, (6) produce draft_review.md with Decision Review Section containing all logged decisions as checkboxes. Should NOT stop for user input between phases.",
      "files": [],
      "assertions": [
        {
          "type": "contains",
          "description": "Runs all phases without stopping for user input",
          "check": "output runs through phases 1-6 sequentially without asking user to confirm between phases"
        },
        {
          "type": "contains",
          "description": "Fetches PMC full text",
          "check": "output runs pmc_fulltext.py or references fetching full text from PMC"
        },
        {
          "type": "contains",
          "description": "Uses confidence-tier screening",
          "check": "output categorizes papers as auto-exclude, auto-include, or uncertain"
        },
        {
          "type": "contains",
          "description": "Produces drug stratification for SGLT2 inhibitors",
          "check": "output identifies individual drugs (empagliflozin, dapagliflozin, canagliflozin) rather than pooling all SGLT2i together"
        },
        {
          "type": "contains",
          "description": "Generates draft_review.md with Decision Review Section",
          "check": "output produces a draft report with checkbox-style decision review section"
        },
        {
          "type": "contains",
          "description": "Logs decisions with rationale throughout",
          "check": "output references decisions_log.json or logs decisions with rationale"
        }
      ]
    },
    {
      "id": 2,
      "prompt": "I need to do a meta-analysis on COVID-19 mortality risk factors. I'm specifically interested in whether obesity increases mortality risk. I already have a list of 12 papers I want to include — how do I extract the data and run the analysis?",
      "expected_output": "Skill should skip phases 1-3 since user has papers already. Should run phases 4-6 autonomously: extract data with effect measure frequency summary, run meta-analysis, produce draft_review.md. Should identify OR or RR as appropriate for mortality binary outcome. Should still produce Decision Review Section for phases 4-6.",
      "files": [],
      "assertions": [
        {
          "type": "contains",
          "description": "Skips search and screening phases since user has papers",
          "check": "output recognizes user already has papers and focuses on extraction and analysis phases"
        },
        {
          "type": "contains",
          "description": "Produces effect measure frequency summary",
          "check": "output surveys how studies report their data and summarizes effect measure frequencies"
        },
        {
          "type": "contains",
          "description": "Recommends OR or RR for binary mortality outcome",
          "check": "output recommends OR or RR as appropriate effect measure for mortality"
        },
        {
          "type": "contains",
          "description": "Generates decision review at the end",
          "check": "output produces decision review checkpoints for user to review"
        }
      ]
    },
    {
      "id": 3,
      "prompt": "Can you help me run a full systematic review comparing laparoscopic vs open appendectomy for complicated appendicitis? I want the whole thing — search, screening, meta-analysis, and a final report with forest plots.",
      "expected_output": "Skill should run all 6 phases autonomously. Should identify this is NOT a pharmacological review so no drug stratification needed. Should identify multiple outcomes (complications as OR, length of stay as MD, mortality as OR). Should produce a single draft_review.md with all decisions as reviewable checkpoints at the end.",
      "files": [],
      "assertions": [
        {
          "type": "contains",
          "description": "Runs fully autonomously through all phases",
          "check": "output runs phases 1-6 without stopping for user confirmation"
        },
        {
          "type": "contains",
          "description": "Correctly identifies non-pharmacological review (no drug stratification)",
          "check": "output does NOT attempt drug stratification for a surgical comparison review"
        },
        {
          "type": "contains",
          "description": "Identifies multiple outcomes with appropriate measures",
          "check": "output identifies at least 2 outcomes (complications, LOS, mortality) with appropriate effect measures (OR for binary, MD for continuous)"
        },
        {
          "type": "contains",
          "description": "Produces consolidated decision review",
          "check": "output generates a single decision review section with all phase decisions as checkboxes"
        }
      ]
    }
  ]
}
```

**Step 2: Commit**

```bash
git add evals/evals.json
git commit -m "feat: update evals for autonomous two-stage workflow"
```

---

### Task 7: Update `references/extraction_templates.md`

Add the new columns for drug stratification and source tracking.

**Files:**
- Modify: `references/extraction_templates.md`

**Step 1: Add drug/dose/source columns to each CSV template**

Add these columns to every outcome data CSV template:
- `drug` — specific drug name (empty for non-pharmacological reviews)
- `dose` — dose tested (empty for non-pharmacological reviews)
- `source_table` — which table in the paper (e.g., "Table 2, row 3")
- `source_notes` — conversions applied

Updated example for OR/RR:
```csv
study,events_treatment,total_treatment,events_control,total_control,drug,dose,source_table,source_notes
Smith 2020,45,230,67,225,empagliflozin,10mg,Table 3 row 2,
Jones 2021,12,89,28,91,dapagliflozin,10mg,Table 2 row 1,SE converted to events using p-value
```

Also add an **Effect Measure Frequency Summary** template section.

**Step 2: Commit**

```bash
git add references/extraction_templates.md
git commit -m "feat: add drug stratification and source tracking columns to extraction templates"
```

---

## Execution Summary

| Task | What | New/Modified |
|------|------|-------------|
| 1 | Decision logger utility | `scripts/decisions_logger.py` (new) |
| 2 | PMC full-text fetcher | `scripts/pmc_fulltext.py` (new) |
| 3 | Decision review report generator | `scripts/generate_review_report.py` (new) |
| 4 | Change detection + rerun logic | `scripts/rerun_from_changes.py` (new) |
| 5 | SKILL.md rewrite | `SKILL.md` (modified) |
| 6 | Eval cases update | `evals/evals.json` (modified) |
| 7 | Extraction templates update | `references/extraction_templates.md` (modified) |

Dependencies: Task 1 should be done first (logger is used by all other components). Tasks 2-4 are independent of each other. Task 5 depends on 1-4 being complete. Tasks 6-7 can be done in parallel with Task 5.
