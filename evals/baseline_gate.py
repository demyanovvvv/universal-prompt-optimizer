#!/usr/bin/env python3
"""Fail CI when the deterministic mock matrix drifts from its golden baseline.

Usage:
    python -B -m evals.baseline_gate --baseline evals/baselines/matrix.json \
        --candidate evals/results/matrix.json

The gate validates the baseline structure, checks the committed fingerprint
against a freshly recomputed one, and diffs the normalized candidate matrix.
Every difference is surfaced in ``failureReasons`` so a failing run explains
itself instead of reporting ``passed: false`` with no detail.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evals.baseline import (
        MODES,
        baseline_fingerprint,
        diff_normalized,
        fingerprint,
        load_baseline,
        normalize_matrix,
        to_matrix_report,
        validate_baseline,
    )
    from evals.quality import compare_reports
except ModuleNotFoundError:  # supports direct script execution
    from baseline import (
        MODES,
        baseline_fingerprint,
        diff_normalized,
        fingerprint,
        load_baseline,
        normalize_matrix,
        to_matrix_report,
        validate_baseline,
    )
    from quality import compare_reports


def _empty_mode_results() -> dict:
    return {
        mode: {
            "passed": False,
            "regressions": [],
            "reliabilityRegressions": [],
            "errors": [],
            "baselineQualityPassRate": 0.0,
            "candidateQualityPassRate": 0.0,
        }
        for mode in MODES
    }


def evaluate(baseline_path: Path, candidate_path: Path) -> dict:
    baseline = load_baseline(baseline_path)
    baseline_errors = validate_baseline(baseline)
    if baseline_errors:
        return {
            "schemaVersion": 1,
            "kind": "baseline-gate",
            "modes": _empty_mode_results(),
            "failureReasons": [f"baseline: {message}" for message in baseline_errors],
            "errors": [],
            "passed": False,
        }
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate_normalized = normalize_matrix(candidate)
    rebuilt = to_matrix_report(baseline)
    baseline_digest = (rebuilt.get("input") or {}).get("sha256")
    candidate_digest = (candidate.get("input") or {}).get("sha256")
    failure_reasons: list[str] = []
    if baseline_digest and candidate_digest and baseline_digest != candidate_digest:
        failure_reasons.append(
            "fixture digest changed: update evals/baselines/matrix.json when fixtures change intentionally"
        )
    recomputed = baseline_fingerprint(baseline)
    if baseline.get("fingerprint") != recomputed:
        failure_reasons.append("baseline fingerprint does not match its contents; regenerate the baseline")
    candidate_fingerprint = fingerprint(candidate_normalized)
    differences = diff_normalized(
        {key: value for key, value in baseline.items() if key not in {"schemaVersion", "kind", "fingerprint"}},
        candidate_normalized,
    )
    if differences:
        failure_reasons.append("matrix drifted from baseline: " + "; ".join(differences))
    mode_results = {}
    errors: list[str] = []
    for mode in MODES:
        comparison = compare_reports(rebuilt, candidate, run_mode=mode)
        mode_results[mode] = {
            "passed": comparison["passed"],
            "regressions": comparison["regressions"],
            "reliabilityRegressions": comparison["reliabilityRegressions"],
            "errors": comparison["errors"],
            "baselineQualityPassRate": comparison["baselineQualityPassRate"],
            "candidateQualityPassRate": comparison["candidateQualityPassRate"],
        }
        errors.extend(f"{mode}: {message}" for message in comparison["errors"])
    return {
        "schemaVersion": 1,
        "kind": "baseline-gate",
        "modes": mode_results,
        "fingerprint": {
            "baseline": baseline.get("fingerprint"),
            "candidate": candidate_fingerprint,
        },
        "failureReasons": failure_reasons,
        "errors": errors,
        "passed": not failure_reasons and not errors and all(item["passed"] for item in mode_results.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the mock matrix against the golden baseline")
    parser.add_argument("--baseline", type=Path, default=Path("evals/baselines/matrix.json"))
    parser.add_argument("--candidate", type=Path, default=Path("evals/results/matrix.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.baseline, args.candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "schemaVersion": 1,
            "kind": "baseline-gate",
            "modes": _empty_mode_results(),
            "failureReasons": [str(exc)],
            "errors": [],
            "passed": False,
        }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
