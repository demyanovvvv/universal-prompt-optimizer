"""Validation and execution of a single provider evaluation case."""

from __future__ import annotations

from typing import Any, Callable


def validate_case(case: Any, index: int) -> None:
    if not isinstance(case, dict):
        raise ValueError(f"case {index} must be an object")
    for field in ("id", "model", "request"):
        if not isinstance(case.get(field), str) or not case[field].strip():
            raise ValueError(f"case {index}: {field} must be a non-empty string")
    if "expect" in case and (not isinstance(case["expect"], list) or not case["expect"] or not all(isinstance(item, str) and item.strip() for item in case["expect"])):
        raise ValueError(f"case {index}: expect must be a non-empty array of strings")
    if "contract" in case and not isinstance(case["contract"], dict):
        raise ValueError(f"case {index}: contract must be an object")


def validate_cases(cases: list[dict[str, Any]], rubric_validator: Callable[[Any, int], None]) -> None:
    ids: set[str] = set()
    for index, case in enumerate(cases, 1):
        validate_case(case, index)
        if "rubric" in case:
            rubric_validator(case["rubric"], index)
        if case["id"] in ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        ids.add(case["id"])
