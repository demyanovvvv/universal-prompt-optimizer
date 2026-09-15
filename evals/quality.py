"""Deterministic response scoring and report regression helpers."""

from __future__ import annotations

import json
from typing import Any


def score_response(response: Any, expected: list[str]) -> dict[str, Any]:
    """Score required phrases against a JSON response without model calls."""
    if not isinstance(expected, list) or not expected or not all(isinstance(item, str) and item.strip() for item in expected):
        raise ValueError("expected must be a non-empty list of strings")
    text = json.dumps(response, ensure_ascii=False, sort_keys=True).casefold()
    missing = [item for item in expected if item.casefold() not in text]
    return {
        "expected": len(expected),
        "matched": len(expected) - len(missing),
        "passed": not missing,
        "missing": missing,
    }


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    min_candidate_rate: float = 0.0,
) -> dict[str, Any]:
    """Compare quality outcomes by stable case ID and report regressions."""
    if not 0 <= min_candidate_rate <= 1:
        raise ValueError("min_candidate_rate must be between 0 and 1")

    def quality_map(report: dict[str, Any]) -> dict[str, bool]:
        results = report.get("caseResults")
        if not isinstance(results, list):
            raise ValueError("report caseResults must be an array")
        values: dict[str, bool] = {}
        for item in results:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("each case result must have a string id")
            if item["id"] in values:
                raise ValueError(f"duplicate case result id: {item['id']}")
            quality = item.get("quality")
            if not isinstance(quality, dict) or not isinstance(quality.get("passed"), bool):
                raise ValueError(f"case {item['id']} is missing quality.passed")
            values[item["id"]] = quality["passed"]
        return values

    baseline_values = quality_map(baseline)
    candidate_values = quality_map(candidate)
    if set(baseline_values) != set(candidate_values):
        raise ValueError("baseline and candidate case IDs must match")
    regressions = sorted(case_id for case_id in baseline_values if baseline_values[case_id] and not candidate_values[case_id])
    baseline_rate = sum(baseline_values.values()) / len(baseline_values) if baseline_values else 0.0
    candidate_rate = sum(candidate_values.values()) / len(candidate_values) if candidate_values else 0.0
    errors = []
    if candidate_rate < min_candidate_rate:
        errors.append(
            f"candidate quality pass rate {candidate_rate:.3f} is below minimum quality pass rate {min_candidate_rate:.3f}"
        )
    return {
        "cases": len(baseline_values),
        "regressions": regressions,
        "baselineQualityPassRate": baseline_rate,
        "candidateQualityPassRate": candidate_rate,
        "errors": errors,
        "passed": not regressions and not errors,
    }
