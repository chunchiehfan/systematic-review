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
