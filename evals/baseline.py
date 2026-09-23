#!/usr/bin/env python3
"""Deterministic golden baseline for the evaluation matrix.

The mock matrix is fully deterministic, so a regression in fixture coverage,
mode joining, quality scoring, or report assembly must fail CI. This module
stores a compact committed baseline (no provider response text) and rebuilds a
comparable matrix report from it, reusing the same comparison logic as the
real-provider workflow.

The baseline pins a normalized fingerprint of the whole matrix: per case and
mode it keeps status, quality counts, and a SHA-256 of the response instead of
the response text, plus the aggregate run/quality/metrics/trace blocks. Only
volatile ``durationMs`` values are excluded, so harness drift is caught.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MODES = ("OFF", "AUTO", "PREVIEW")
KIND = "matrix-baseline"

_QUALITY_FIELDS = ("expected", "matched", "passed", "missing", "forbidden", "score", "fields", "exact")


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_quality(quality: Any) -> dict[str, Any]:
    if not isinstance(quality, dict):
        return {}
    return {field: quality[field] for field in _QUALITY_FIELDS if field in quality}


def _normalize_mode_result(result: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"status": result.get("status")}
    quality = _normalize_quality(result.get("quality"))
    if quality:
        entry["quality"] = quality
        entry["qualityPassed"] = bool(quality.get("passed"))
    if "response" in result:
        entry["responseSha256"] = _digest(result["response"])
    metrics = result.get("metrics")
    if isinstance(metrics, dict):
        entry["metrics"] = metrics
    trace = result.get("trace")
    if isinstance(trace, list):
        entry["traceEvents"] = len(trace)
    if result.get("status") == "failed":
        entry["error"] = result.get("error")
    return entry


def normalize_matrix(report: dict[str, Any]) -> dict[str, Any]:
    """Reduce a matrix report to a deterministic, duration-free fingerprint."""
    if report.get("mode") != "matrix":
        raise ValueError("only matrix reports can be normalized")
    cases = report.get("caseResults")
    if not isinstance(cases, list) or not cases:
        raise ValueError("matrix report must contain caseResults")
    normalized_cases = []
    seen: set[str] = set()
    for item in cases:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("each case result must have a string id")
        if item["id"] in seen:
            raise ValueError(f"duplicate case id: {item['id']}")
        seen.add(item["id"])
        results = item.get("results")
        if not isinstance(results, dict):
            raise ValueError(f"case {item['id']} is missing results")
        modes: dict[str, Any] = {}
        for mode in MODES:
            result = results.get(mode)
            if not isinstance(result, dict):
                raise ValueError(f"case {item['id']} is missing mode {mode}")
            modes[mode] = _normalize_mode_result(result)
        normalized_cases.append({"id": item["id"], "modes": modes})
    normalized_cases.sort(key=lambda entry: entry["id"])
    input_meta = report.get("input") if isinstance(report.get("input"), dict) else {}
    normalized: dict[str, Any] = {
        "modes": list(MODES),
        "input": {"format": input_meta.get("format"), "sha256": input_meta.get("sha256")},
        "providerCalls": report.get("providerCalls"),
        "failures": report.get("failures", 0),
        "runs": report.get("runs"),
        "quality": report.get("quality"),
        "metrics": report.get("metrics"),
        "trace": report.get("trace"),
        "cases": normalized_cases,
    }
    return normalized


def fingerprint(normalized: dict[str, Any]) -> str:
    return _digest(normalized)


def summarize_matrix(report: dict[str, Any]) -> dict[str, Any]:
    """Reduce a matrix report to the deterministic invariants worth pinning."""
    normalized = normalize_matrix(report)
    return {
        "schemaVersion": 1,
        "kind": KIND,
        "fingerprint": fingerprint(normalized),
        **normalized,
    }


def validate_baseline(baseline: Any) -> list[str]:
    """Return structural errors for a baseline object; valid baselines return []."""
    errors: list[str] = []
    if not isinstance(baseline, dict):
        return ["baseline must be an object"]
    if baseline.get("schemaVersion") != 1:
        errors.append("baseline.schemaVersion must be 1")
    if baseline.get("kind") != KIND:
        errors.append(f"baseline.kind must be {KIND}")
    if baseline.get("modes") != list(MODES):
        errors.append(f"baseline.modes must be {list(MODES)}")
    input_meta = baseline.get("input")
    if not isinstance(input_meta, dict):
        errors.append("baseline.input must be an object")
    else:
        digest = input_meta.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            errors.append("baseline.input.sha256 must be a 64-character hex digest")
    cases = baseline.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("baseline.cases must be a non-empty array")
        return errors
    ids: set[str] = set()
    for index, item in enumerate(cases):
        path = f"baseline.cases[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            errors.append(f"{path}.id must be a non-empty string")
            continue
        if item["id"] in ids:
            errors.append(f"{path}.id is duplicated: {item['id']}")
        ids.add(item["id"])
        modes = item.get("modes")
        if not isinstance(modes, dict) or set(modes) != set(MODES):
            errors.append(f"{path}.modes must contain OFF, AUTO, and PREVIEW")
            continue
        for mode in MODES:
            entry = modes[mode]
            entry_path = f"{path}.modes.{mode}"
            if not isinstance(entry, dict):
                errors.append(f"{entry_path} must be an object")
                continue
            if not isinstance(entry.get("status"), str):
                errors.append(f"{entry_path}.status must be a string")
            if not isinstance(entry.get("qualityPassed"), bool):
                errors.append(f"{entry_path}.qualityPassed must be a boolean")
            if "responseSha256" in entry and (
                not isinstance(entry["responseSha256"], str) or len(entry["responseSha256"]) != 64
            ):
                errors.append(f"{entry_path}.responseSha256 must be a 64-character hex digest")
    stored = baseline.get("fingerprint")
    if not isinstance(stored, str) or len(stored) != 64:
        errors.append("baseline.fingerprint must be a 64-character hex digest")
    return errors


def baseline_fingerprint(baseline: dict[str, Any]) -> str:
    """Recompute the fingerprint from a baseline's normalized payload."""
    payload = {key: value for key, value in baseline.items() if key not in {"schemaVersion", "kind", "fingerprint"}}
    return fingerprint(payload)


def diff_normalized(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Return human-readable differences between two normalized matrices."""
    differences: list[str] = []
    for key in ("input", "providerCalls", "failures", "runs", "quality", "metrics", "trace"):
        if baseline.get(key) != candidate.get(key):
            differences.append(f"{key} changed")
    baseline_cases = {item["id"]: item["modes"] for item in baseline.get("cases", [])}
    candidate_cases = {item["id"]: item["modes"] for item in candidate.get("cases", [])}
    for case_id in sorted(set(baseline_cases) - set(candidate_cases)):
        differences.append(f"case removed: {case_id}")
    for case_id in sorted(set(candidate_cases) - set(baseline_cases)):
        differences.append(f"case added: {case_id}")
    for case_id in sorted(set(baseline_cases) & set(candidate_cases)):
        for mode in MODES:
            if baseline_cases[case_id].get(mode) != candidate_cases[case_id].get(mode):
                differences.append(f"case {case_id} mode {mode} changed")
    return differences


def to_matrix_report(baseline: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a matrix report comparable with compare_reports()."""
    if baseline.get("kind") != KIND:
        raise ValueError(f"baseline kind must be {KIND}")
    cases = baseline.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("baseline must contain cases")
    joined = []
    for item in cases:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("each baseline case must have a string id")
        modes = item.get("modes")
        if not isinstance(modes, dict):
            raise ValueError(f"baseline case {item['id']} is missing modes")
        results = {}
        for mode in MODES:
            entry = modes.get(mode)
            if not isinstance(entry, dict) or not isinstance(entry.get("qualityPassed"), bool):
                raise ValueError(f"baseline case {item['id']} mode {mode} is invalid")
            results[mode] = {
                "id": item["id"],
                "status": entry.get("status", "measured"),
                "quality": {"passed": entry["qualityPassed"]},
            }
        joined.append({"id": item["id"], "results": results})
    input_meta = baseline.get("input") if isinstance(baseline.get("input"), dict) else {}
    return {
        "schemaVersion": 1,
        "mode": "matrix",
        "modes": list(MODES),
        "caseResults": joined,
        "input": {"format": input_meta.get("format"), "sha256": input_meta.get("sha256")},
    }


def load_baseline(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("baseline root must be an object")
    return data
