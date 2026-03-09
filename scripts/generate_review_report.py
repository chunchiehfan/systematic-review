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
