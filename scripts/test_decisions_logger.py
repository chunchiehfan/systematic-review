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
