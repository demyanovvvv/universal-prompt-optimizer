#!/usr/bin/env python3
"""Compare two provider quality reports without making provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.quality import compare_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare provider evaluation quality reports")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--min-quality-pass-rate", type=float, default=0.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.min_quality_pass_rate <= 1:
        parser.error("--min-quality-pass-rate must be between 0 and 1")
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        comparison = compare_reports(
            baseline,
            candidate,
            min_candidate_rate=args.min_quality_pass_rate,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        comparison = {"passed": False, "errors": [str(exc)]}
    encoded = json.dumps(comparison, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if comparison["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
