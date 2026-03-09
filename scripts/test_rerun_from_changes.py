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
