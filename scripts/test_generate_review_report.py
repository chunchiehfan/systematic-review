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
        self.assertIn("pico_definition", md.lower().replace(" ", "_") or md)

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
