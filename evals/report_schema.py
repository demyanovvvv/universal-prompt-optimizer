"""Dependency-free validation for evaluation report contracts."""

from __future__ import annotations

import math
import json
from typing import Any


_TOKEN_METRICS = {"inputTokens", "outputTokens", "reasoningTokens", "cachedTokens"}
_NUMERIC_METRICS = _TOKEN_METRICS | {"cost"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_quality(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for field in ("expected", "matched"):
        if not isinstance(value.get(field), int) or isinstance(value.get(field), bool) or value[field] < 0:
            errors.append(f"{path}.{field} must be a non-negative integer")
    if all(isinstance(value.get(field), int) and not isinstance(value.get(field), bool) for field in ("expected", "matched")) and value.get("matched", 0) > value.get("expected", 0):
        errors.append(f"{path}.matched cannot exceed expected")
    if not isinstance(value.get("passed"), bool):
        errors.append(f"{path}.passed must be a boolean")
    if not isinstance(value.get("missing"), list) or not all(isinstance(item, str) for item in value.get("missing", [])):
        errors.append(f"{path}.missing must be an array of strings")
    if "score" in value and (not _is_number(value["score"]) or not math.isfinite(value["score"]) or not 0 <= value["score"] <= 1):
        errors.append(f"{path}.score must be a number between 0 and 1")
    if "forbidden" in value and (not isinstance(value["forbidden"], list) or not all(isinstance(item, str) for item in value["forbidden"])):
        errors.append(f"{path}.forbidden must be an array of strings")
    if "fields" in value:
        fields = value["fields"]
        if not isinstance(fields, dict) or not isinstance(fields.get("expected"), list) or not isinstance(fields.get("missing"), list) or not isinstance(fields.get("passed"), bool):
            errors.append(f"{path}.fields must contain expected, missing, and passed")
    if "exact" in value:
        exact = value["exact"]
        if not isinstance(exact, dict) or not isinstance(exact.get("passed"), bool) or not isinstance(exact.get("matched"), bool):
            errors.append(f"{path}.exact must contain boolean passed and matched")


def _validate_metrics(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for name, metric in value.items():
        if name not in _NUMERIC_METRICS:
            errors.append(f"{path}.{name} is unsupported")
            continue
        if not _is_number(metric) or not math.isfinite(metric) or metric < 0:
            errors.append(f"{path}.{name} must be a non-negative finite number")
        elif name in _TOKEN_METRICS and not isinstance(metric, int):
            errors.append(f"{path}.{name} must be a non-negative integer")


def _validate_latency(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for field in ("measured", "p50Ms", "p95Ms"):
        metric = value.get(field)
        if metric is None and field != "measured":
            continue
        if not isinstance(metric, int) or isinstance(metric, bool) or metric < 0:
            errors.append(f"{path}.{field} must be null or a non-negative integer")
    if isinstance(value.get("p50Ms"), int) and isinstance(value.get("p95Ms"), int) and value["p95Ms"] < value["p50Ms"]:
        errors.append(f"{path}.p95Ms cannot be less than p50Ms")


def _validate_trace(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) > 100:
        errors.append(f"{path} must be an array with at most 100 events")
        return
    for index, event in enumerate(value):
        if not isinstance(event, dict) or not isinstance(event.get("event"), str) or not event["event"].strip():
            errors.append(f"{path}[{index}].event must be a non-empty string")
    try:
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 65_536:
            errors.append(f"{path} exceeds 65536 bytes")
    except (TypeError, ValueError):
        errors.append(f"{path} must be JSON-serializable")


def _validate_aggregate_metrics(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    available = value.get("available")
    totals = value.get("total")
    if not isinstance(available, list) or not all(isinstance(item, str) and item in _NUMERIC_METRICS for item in available):
        errors.append(f"{path}.available must be an array of supported metric names")
    if not isinstance(totals, dict):
        errors.append(f"{path}.total must be an object")
    else:
        _validate_metrics(totals, f"{path}.total", errors)
        if isinstance(available, list) and set(totals) != set(available):
            errors.append(f"{path}.available must match {path}.total keys")


def _validate_aggregate_quality(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    for field in ("cases", "scored", "passed"):
        if not isinstance(value.get(field), int) or isinstance(value.get(field), bool) or value[field] < 0:
            errors.append(f"{path}.{field} must be a non-negative integer")
    if isinstance(value.get("scored"), int) and isinstance(value.get("cases"), int) and value["scored"] > value["cases"]:
        errors.append(f"{path}.scored cannot exceed {path}.cases")
    if isinstance(value.get("passed"), int) and isinstance(value.get("scored"), int) and value["passed"] > value["scored"]:
        errors.append(f"{path}.passed cannot exceed {path}.scored")
    if value.get("passRate") is not None:
        if not _is_number(value["passRate"]) or not math.isfinite(value["passRate"]) or not 0 <= value["passRate"] <= 1:
            errors.append(f"{path}.passRate must be null or a finite number between 0 and 1")


def _validate_case_result(value: Any, path: str, errors: list[str], *, matrix: bool = False) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return
    if not isinstance(value.get("id"), str) or not value["id"].strip():
        errors.append(f"{path}.id must be a non-empty string")
    if matrix:
        results = value.get("results")
        if not isinstance(results, dict):
            errors.append(f"{path}.results must be an object")
        else:
            for mode, result in results.items():
                _validate_case_result(result, f"{path}.results.{mode}", errors)
        return
    if value.get("status") not in {"measured", "failed", "approval_required"}:
        errors.append(f"{path}.status must be measured, failed, or approval_required")
    if "durationMs" in value and (not isinstance(value["durationMs"], int) or isinstance(value["durationMs"], bool) or value["durationMs"] < 0):
        errors.append(f"{path}.durationMs must be a non-negative integer")
    if "quality" in value:
        _validate_quality(value["quality"], f"{path}.quality", errors)
    if "metrics" in value:
        _validate_metrics(value["metrics"], f"{path}.metrics", errors)
    if "trace" in value:
        _validate_trace(value["trace"], f"{path}.trace", errors)


def validate_report(report: Any, kind: str) -> list[str]:
    """Return contract errors for a report; valid reports return an empty list."""
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if report.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if kind == "provider":
        if report.get("mode") not in {"OFF", "AUTO", "PREVIEW"}:
            errors.append("mode must be OFF, AUTO, or PREVIEW")
        for field in ("providerCalls", "failures"):
            if not isinstance(report.get(field), int) or isinstance(report.get(field), bool) or report[field] < 0:
                errors.append(f"{field} must be a non-negative integer")
        if not isinstance(report.get("caseResults"), list):
            errors.append("caseResults must be an array")
        else:
            ids: set[str] = set()
            for index, item in enumerate(report["caseResults"]):
                _validate_case_result(item, f"caseResults[{index}]", errors)
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    if item["id"] in ids:
                        errors.append(f"caseResults contains duplicate id {item['id']}")
                    ids.add(item["id"])
        summary = report.get("summary")
        if not isinstance(summary, dict):
            errors.append("summary must be an object")
        else:
            for field in ("cases", "measured", "approvalRequired", "failed"):
                if not isinstance(summary.get(field), int) or isinstance(summary.get(field), bool) or summary[field] < 0:
                    errors.append(f"summary.{field} must be a non-negative integer")
        quality = report.get("quality")
        if quality is not None:
            if not isinstance(quality, dict):
                errors.append("quality must be an object")
            else:
                for field in ("cases", "scored", "passed"):
                    if not isinstance(quality.get(field), int) or isinstance(quality.get(field), bool) or quality[field] < 0:
                        errors.append(f"quality.{field} must be a non-negative integer")
                if quality.get("scored", 0) > quality.get("cases", 0):
                    errors.append("quality.scored cannot exceed quality.cases")
                if quality.get("passed", 0) > quality.get("scored", 0):
                    errors.append("quality.passed cannot exceed quality.scored")
                if quality.get("passRate") is not None and (not _is_number(quality["passRate"]) or not math.isfinite(quality["passRate"]) or not 0 <= quality["passRate"] <= 1):
                    errors.append("quality.passRate must be null or a number between 0 and 1")
                if quality.get("passRate") is not None and quality.get("scored", 0) > 0:
                    expected_rate = quality["passed"] / quality["scored"]
                    if abs(quality["passRate"] - expected_rate) > 1e-9:
                        errors.append("quality.passRate must equal quality.passed / quality.scored")
        if "metrics" in report:
            _validate_aggregate_metrics(report["metrics"], "metrics", errors)
        if "latency" in report:
            _validate_latency(report["latency"], "latency", errors)
        if "trace" in report and (not isinstance(report["trace"], dict) or not isinstance(report["trace"].get("events"), int) or report["trace"]["events"] < 0):
            errors.append("trace.events must be a non-negative integer")
    elif kind == "matrix":
        if report.get("mode") != "matrix":
            errors.append("mode must be matrix")
        if report.get("modes") != ["OFF", "AUTO", "PREVIEW"]:
            errors.append("modes must be [OFF, AUTO, PREVIEW]")
        if not isinstance(report.get("providerCalls"), int) or isinstance(report.get("providerCalls"), bool) or report["providerCalls"] < 0:
            errors.append("providerCalls must be a non-negative integer")
        if not isinstance(report.get("caseResults"), list):
            errors.append("caseResults must be an array")
        else:
            for index, item in enumerate(report["caseResults"]):
                _validate_case_result(item, f"caseResults[{index}]", errors, matrix=True)
        if not isinstance(report.get("runs"), dict):
            errors.append("runs must be an object")
        for field in ("quality", "metrics"):
            if field in report and not isinstance(report[field], dict):
                errors.append(f"{field} must be an object")
        if isinstance(report.get("quality"), dict):
            for mode, quality in report["quality"].items():
                _validate_aggregate_quality(quality, f"quality.{mode}", errors)
        if isinstance(report.get("metrics"), dict):
            for mode, metrics in report["metrics"].items():
                _validate_aggregate_metrics(metrics, f"metrics.{mode}", errors)
    elif kind == "deterministic":
        if report.get("mode") != "deterministic":
            errors.append("mode must be deterministic")
        if report.get("providerCalls") != 0:
            errors.append("providerCalls must be 0")
        if not isinstance(report.get("caseResults"), list):
            errors.append("caseResults must be an array")
    elif kind == "baseline-gate":
        if report.get("kind") != "baseline-gate":
            errors.append("kind must be baseline-gate")
        modes = report.get("modes")
        if not isinstance(modes, dict):
            errors.append("modes must be an object")
        else:
            if set(modes) != {"OFF", "AUTO", "PREVIEW"}:
                errors.append("modes must contain OFF, AUTO, and PREVIEW")
            for mode, entry in modes.items():
                path = f"modes.{mode}"
                if not isinstance(entry, dict):
                    errors.append(f"{path} must be an object")
                    continue
                if not isinstance(entry.get("passed"), bool):
                    errors.append(f"{path}.passed must be a boolean")
                for field in ("regressions", "reliabilityRegressions", "errors"):
                    if not isinstance(entry.get(field), list) or not all(isinstance(item, str) for item in entry.get(field, [])):
                        errors.append(f"{path}.{field} must be an array of strings")
        for field in ("errors", "failureReasons"):
            if not isinstance(report.get(field), list) or not all(isinstance(item, str) for item in report.get(field, [])):
                errors.append(f"{field} must be an array of strings")
        fingerprint = report.get("fingerprint")
        if fingerprint is not None:
            if not isinstance(fingerprint, dict):
                errors.append("fingerprint must be an object")
            else:
                for field in ("baseline", "candidate"):
                    value = fingerprint.get(field)
                    if value is not None and (not isinstance(value, str) or len(value) != 64):
                        errors.append(f"fingerprint.{field} must be a 64-character hex digest or null")
    elif kind == "comparison":
        if not isinstance(report.get("passed"), bool):
            errors.append("passed must be a boolean")
        for field in ("regressions", "reliabilityRegressions", "latencyRegressions", "costRegressions", "addedCases", "removedCases", "warnings", "errors"):
            if field in report and (not isinstance(report[field], list) or not all(isinstance(item, str) for item in report[field])):
                errors.append(f"{field} must be an array of strings")
    else:
        errors.append(f"unknown report kind: {kind}")
    if not isinstance(report.get("passed"), bool):
        errors.append("passed must be a boolean")
    return errors
