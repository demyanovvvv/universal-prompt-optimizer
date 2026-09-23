#!/usr/bin/env python3
"""Validate a saved evaluation report against its runtime contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evals.report_schema import validate_report
except ModuleNotFoundError:  # supports direct script execution
    from report_schema import validate_report


def infer_kind(report: dict) -> str:
    mode = report.get("mode")
    if mode == "deterministic":
        return "deterministic"
    if mode == "matrix":
        return "matrix"
    if mode in {"OFF", "AUTO", "PREVIEW"}:
        return "provider"
    if "baselineQualityPassRate" in report or "candidateQualityPassRate" in report:
        return "comparison"
    if report.get("kind") == "baseline-gate":
        return "baseline-gate"
    raise ValueError("unable to infer report kind; pass --kind")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a saved evaluation report")
    parser.add_argument("report", type=Path)
    parser.add_argument("--kind", choices=["provider", "matrix", "deterministic", "comparison", "baseline-gate"])
    args = parser.parse_args()
    try:
        value = json.loads(args.report.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("report JSON must be an object")
        kind = args.kind or infer_kind(value)
        errors = validate_report(value, kind)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"passed": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    result = {"kind": kind, "passed": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
