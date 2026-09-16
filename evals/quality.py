"""Deterministic response scoring and report regression helpers."""

from __future__ import annotations

import json
import math
from typing import Any


def score_exact_match(actual: Any, expected: Any) -> dict[str, bool]:
    matched = actual == expected
    return {"passed": matched, "matched": matched}


def score_response(
    response: Any,
    expected: list[str],
    *,
    rubric: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score required phrases against a JSON response without model calls."""
    if not isinstance(expected, list) or not expected or not all(isinstance(item, str) and item.strip() for item in expected):
        raise ValueError("expected must be a non-empty list of strings")
    text = json.dumps(response, ensure_ascii=False, sort_keys=True).casefold()
    missing = [item for item in expected if item.casefold() not in text]
    result: dict[str, Any] = {
        "expected": len(expected),
        "matched": len(expected) - len(missing),
        "passed": not missing,
        "missing": missing,
    }
    if rubric is None:
        return result
    if not isinstance(rubric, dict):
        raise ValueError("rubric must be an object")
    forbidden = rubric.get("forbidden", [])
    if not isinstance(forbidden, list) or not all(isinstance(item, str) and item.strip() for item in forbidden):
        raise ValueError("rubric.forbidden must be an array of non-empty strings")
    min_score = rubric.get("minScore", 1.0)
    if not isinstance(min_score, (int, float)) or isinstance(min_score, bool) or not 0 <= min_score <= 1:
        raise ValueError("rubric.minScore must be between 0 and 1")
    found_forbidden = [item for item in forbidden if item.casefold() in text]
    score = (len(expected) - len(missing)) / len(expected)
    required_fields = rubric.get("requiredFields", [])
    if not isinstance(required_fields, list) or not all(isinstance(item, str) and item.strip() for item in required_fields):
        raise ValueError("rubric.requiredFields must be an array of non-empty strings")
    fields = {
        "expected": required_fields,
        "missing": [item for item in required_fields if not isinstance(response, dict) or item not in response],
    }
    fields["passed"] = not fields["missing"]
    exact = None
    if "exact" in rubric:
        exact = score_exact_match(response, rubric["exact"])
    result.update({
        "score": score,
        "forbidden": found_forbidden,
        "passed": not missing and not found_forbidden and score >= min_score,
    })
    if required_fields:
        result["fields"] = fields
        result["passed"] = result["passed"] and fields["passed"]
    if exact is not None:
        result["exact"] = exact
        result["passed"] = result["passed"] and exact["passed"]
    return result


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    min_candidate_rate: float = 0.0,
    max_quality_drop: float = 1.0,
    max_latency_increase: float = 1.0,
    max_cost_increase: float = 1.0,
    allow_fixture_change: bool = False,
    run_mode: str | None = None,
) -> dict[str, Any]:
    """Compare quality outcomes by stable case ID and report regressions."""
    if not math.isfinite(min_candidate_rate) or not 0 <= min_candidate_rate <= 1:
        raise ValueError("min_candidate_rate must be between 0 and 1")
    if not math.isfinite(max_quality_drop) or not 0 <= max_quality_drop <= 1:
        raise ValueError("max_quality_drop must be between 0 and 1")
    if not math.isfinite(max_latency_increase) or not math.isfinite(max_cost_increase) or max_latency_increase < 0 or max_cost_increase < 0:
        raise ValueError("metric increase thresholds must be non-negative")

    def result_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
        if report.get("mode") == "matrix" and run_mode is None:
            raise ValueError("run_mode is required when comparing matrix reports")
        results = report.get("caseResults")
        if not isinstance(results, list):
            raise ValueError("report caseResults must be an array")
        values: dict[str, dict[str, Any]] = {}
        for item in results:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("each case result must have a string id")
            if item["id"] in values:
                raise ValueError(f"duplicate case result id: {item['id']}")
            if run_mode is not None and report.get("mode") == "matrix":
                mode_result = item.get("results", {}).get(run_mode)
                if not isinstance(mode_result, dict):
                    raise ValueError(f"case {item['id']} is missing matrix mode {run_mode}")
                item = mode_result | {"id": item["id"]}
            quality = item.get("quality")
            if not isinstance(quality, dict) or not isinstance(quality.get("passed"), bool):
                raise ValueError(f"case {item['id']} is missing quality.passed")
            values[item["id"]] = item
        return values

    baseline_values = result_map(baseline)
    candidate_values = result_map(candidate)
    baseline_ids = set(baseline_values)
    candidate_ids = set(candidate_values)
    added_cases = sorted(candidate_ids - baseline_ids)
    removed_cases = sorted(baseline_ids - candidate_ids)
    comparable_ids = baseline_ids & candidate_ids
    regressions = sorted(
        case_id
        for case_id in comparable_ids
        if baseline_values[case_id]["quality"]["passed"] and not candidate_values[case_id]["quality"]["passed"]
    )
    baseline_rate = sum(item["quality"]["passed"] for item in baseline_values.values()) / len(baseline_values) if baseline_values else 0.0
    candidate_rate = sum(item["quality"]["passed"] for item in candidate_values.values()) / len(candidate_values) if candidate_values else 0.0
    reliability_regressions = sorted(
        case_id
        for case_id, baseline_item in baseline_values.items()
        if case_id in candidate_values
        if baseline_item.get("status") == "measured" and candidate_values[case_id].get("status") != "measured"
    )
    latency_regressions: list[str] = []
    cost_regressions: list[str] = []
    for case_id, baseline_item in baseline_values.items():
        if case_id not in candidate_values:
            continue
        candidate_item = candidate_values[case_id]
        baseline_duration = baseline_item.get("durationMs")
        candidate_duration = candidate_item.get("durationMs")
        if isinstance(baseline_duration, (int, float)) and baseline_duration > 0 and isinstance(candidate_duration, (int, float)):
            if (candidate_duration - baseline_duration) / baseline_duration > max_latency_increase:
                latency_regressions.append(case_id)
        baseline_cost = (baseline_item.get("metrics") or {}).get("cost") if isinstance(baseline_item.get("metrics"), dict) else None
        candidate_cost = (candidate_item.get("metrics") or {}).get("cost") if isinstance(candidate_item.get("metrics"), dict) else None
        if isinstance(baseline_cost, (int, float)) and baseline_cost > 0 and isinstance(candidate_cost, (int, float)):
            if (candidate_cost - baseline_cost) / baseline_cost > max_cost_increase:
                cost_regressions.append(case_id)
    errors = []
    warnings = []
    if added_cases:
        warnings.append(f"candidate added cases: {', '.join(added_cases)}")
    if removed_cases:
        warnings.append(f"candidate removed cases: {', '.join(removed_cases)}")
    baseline_digest = baseline.get("input", {}).get("sha256") if isinstance(baseline.get("input"), dict) else None
    candidate_digest = candidate.get("input", {}).get("sha256") if isinstance(candidate.get("input"), dict) else None
    if baseline_digest and candidate_digest and baseline_digest != candidate_digest and not allow_fixture_change:
        errors.append("fixture digest changed; pass allow_fixture_change=True to compare changed fixtures")
    if candidate_rate < min_candidate_rate:
        errors.append(
            f"candidate quality pass rate {candidate_rate:.3f} is below minimum quality pass rate {min_candidate_rate:.3f}"
        )
    if baseline_rate - candidate_rate > max_quality_drop:
        errors.append(
            f"quality pass rate dropped by {baseline_rate - candidate_rate:.3f}, above maximum quality drop {max_quality_drop:.3f}"
        )
    return {
        "schemaVersion": 1,
        "cases": len(baseline_values),
        "regressions": regressions,
        "baselineQualityPassRate": baseline_rate,
        "candidateQualityPassRate": candidate_rate,
        "addedCases": added_cases,
        "removedCases": removed_cases,
        "warnings": warnings,
        "reliabilityRegressions": reliability_regressions,
        "latencyRegressions": sorted(latency_regressions),
        "costRegressions": sorted(cost_regressions),
        "errors": errors,
        "passed": not regressions and not reliability_regressions and not latency_regressions and not cost_regressions and not errors and not added_cases and not removed_cases,
    }
