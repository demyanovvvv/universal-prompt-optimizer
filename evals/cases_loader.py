"""JSONL fixture loading independent from provider execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: case must be an object")
        cases.append(value)
    return cases


def select_cases(cases: list[dict[str, Any]], selected: list[str] | None) -> list[dict[str, Any]]:
    if not selected:
        return cases
    available = {case.get("id") for case in cases}
    unknown = [case_id for case_id in selected if case_id not in available]
    if unknown:
        raise ValueError(f"unknown case id: {', '.join(unknown)}")
    selected_set = set(selected)
    return [case for case in cases if case.get("id") in selected_set]
