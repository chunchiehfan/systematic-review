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
