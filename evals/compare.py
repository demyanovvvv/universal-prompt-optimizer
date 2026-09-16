#!/usr/bin/env python3
"""Compare two provider quality reports without making provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evals.quality import compare_reports
except ModuleNotFoundError:  # supports direct script execution
    from quality import compare_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare provider evaluation quality reports")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--min-quality-pass-rate", type=float, default=0.0)
    parser.add_argument("--max-quality-drop", type=float, default=1.0)
    parser.add_argument("--max-latency-increase", type=float, default=1.0)
    parser.add_argument("--max-cost-increase", type=float, default=1.0)
    parser.add_argument("--allow-fixture-change", action="store_true")
    parser.add_argument("--run-mode", choices=["OFF", "AUTO", "PREVIEW"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.min_quality_pass_rate <= 1 or not 0 <= args.max_quality_drop <= 1:
        parser.error("quality thresholds must be between 0 and 1")
    if args.max_latency_increase < 0 or args.max_cost_increase < 0:
        parser.error("metric increase thresholds must be non-negative")
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        comparison = compare_reports(
            baseline,
            candidate,
            min_candidate_rate=args.min_quality_pass_rate,
            max_quality_drop=args.max_quality_drop,
            max_latency_increase=args.max_latency_increase,
            max_cost_increase=args.max_cost_increase,
            allow_fixture_change=args.allow_fixture_change,
            run_mode=args.run_mode,
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
