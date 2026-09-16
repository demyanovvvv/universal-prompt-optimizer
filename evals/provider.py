"""Opt-in provider harness for measured OFF/AUTO/PREVIEW fixture runs.

The provider is deliberately injected by the caller. This module never reads
credentials, performs network requests, or pretends to evaluate a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

try:
    from evals.quality import score_response
    from evals.report_schema import validate_report
    from evals.redaction import redact_sensitive
except ModuleNotFoundError:  # supports direct execution from the evals directory
    from quality import score_response
    from report_schema import validate_report
    from redaction import redact_sensitive


MODES = {"OFF", "AUTO", "PREVIEW"}
TOKEN_METRICS = {"inputTokens", "outputTokens", "reasoningTokens", "cachedTokens"}
NUMERIC_METRICS = TOKEN_METRICS | {"cost"}
MAX_TRACE_EVENTS = 100
MAX_TRACE_BYTES = 65_536


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _unpack_provider_response(value: Any) -> tuple[Any, dict[str, int | float]]:
    """Unpack the optional response envelope and validate bounded metrics."""
    if not isinstance(value, dict) or ("response" not in value and "metrics" not in value):
        return value, {}
    if "response" not in value:
        raise ValueError("provider envelope must include response")
    metrics = value.get("metrics", {})
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object")
    unknown = sorted(set(metrics) - NUMERIC_METRICS)
    if unknown:
        raise ValueError(f"metrics contains unsupported fields: {unknown}")
    normalized: dict[str, int | float] = {}
    for name, metric in metrics.items():
        if not isinstance(metric, (int, float)) or isinstance(metric, bool) or not math.isfinite(metric) or metric < 0:
            raise ValueError(f"metrics.{name} must be a non-negative finite number")
        if name in TOKEN_METRICS and (not isinstance(metric, int) or isinstance(metric, bool)):
            raise ValueError(f"metrics.{name} must be a non-negative integer")
        normalized[name] = metric
    return value["response"], normalized


def _unpack_trace(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_TRACE_EVENTS:
        raise ValueError(f"trace must be an array with at most {MAX_TRACE_EVENTS} events")
    trace: list[dict[str, Any]] = []
    for index, event in enumerate(value):
        if not isinstance(event, dict) or not isinstance(event.get("event"), str) or not event["event"].strip():
            raise ValueError(f"trace[{index}].event must be a non-empty string")
        trace.append(redact_sensitive(event))
    if len(json.dumps(trace, ensure_ascii=False).encode("utf-8")) > MAX_TRACE_BYTES:
        raise ValueError(f"trace exceeds {MAX_TRACE_BYTES} bytes")
    return trace


def _validate_rubric(rubric: Any, index: int) -> None:
    if not isinstance(rubric, dict):
        raise ValueError(f"case {index}: rubric must be an object")
    forbidden = rubric.get("forbidden", [])
    if not isinstance(forbidden, list) or not all(isinstance(item, str) and item.strip() for item in forbidden):
        raise ValueError(f"case {index}: rubric.forbidden must be an array of non-empty strings")
    required_fields = rubric.get("requiredFields", [])
    if not isinstance(required_fields, list) or not all(isinstance(item, str) and item.strip() for item in required_fields):
        raise ValueError(f"case {index}: rubric.requiredFields must be an array of non-empty strings")
    min_score = rubric.get("minScore", 1.0)
    if not isinstance(min_score, (int, float)) or isinstance(min_score, bool) or not math.isfinite(min_score) or not 0 <= min_score <= 1:
        raise ValueError(f"case {index}: rubric.minScore must be finite and between 0 and 1")
    if "exact" in rubric and not isinstance(rubric["exact"], (dict, list, str, int, float, bool, type(None))):
        raise ValueError(f"case {index}: rubric.exact must be JSON-compatible")


def cli_provider(
    command: list[str],
    payload: dict[str, Any],
    *,
    timeout: float = 60,
    max_output_bytes: int = 1_048_576,
) -> Any:
    """Call an explicit provider executable using a JSON stdin/stdout protocol."""
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("provider command must be a non-empty argv list")
    if max_output_bytes < 1:
        raise ValueError("max_output_bytes must be positive")
    encoded_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            completed = subprocess.run(
                command,
                input=encoded_payload,
                stdout=stdout_file,
                stderr=stderr_file,
                check=False,
                shell=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"provider timed out after {timeout:g}s") from exc
        stderr_file.seek(0)
        if completed.returncode:
            detail = stderr_file.read(65_536).decode("utf-8", errors="replace").strip() or "no stderr"
            raise RuntimeError(f"provider exited with {completed.returncode}: {detail}")
        stdout_file.seek(0, 2)
        output_bytes = stdout_file.tell()
        if output_bytes > max_output_bytes:
            raise RuntimeError(f"provider stdout exceeds {max_output_bytes} bytes")
        stdout_file.seek(0)
        try:
            output = stdout_file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"provider returned invalid UTF-8: {exc}") from exc
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"provider returned invalid JSON: {exc}") from exc


def run_provider_cases(
    cases: Iterable[dict[str, Any]],
    *,
    mode: str,
    provider: Callable[[dict[str, Any]], Any],
    approve: bool = False,
    input_path: Path | None = None,
    max_response_bytes: int = 1_048_576,
    max_cases: int = 1000,
) -> dict[str, Any]:
    """Run injected provider calls under an explicit harness mode.

    PREVIEW is approval-gated and performs no provider call until approved.
    The provider receives the original fixture request and mode, leaving prompt
    optimization and provider-specific payloads to the caller.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    if max_response_bytes < 1:
        raise ValueError("max_response_bytes must be positive")
    if max_cases < 1:
        raise ValueError("max_cases must be positive")

    cases = list(cases)
    if len(cases) > max_cases:
        raise ValueError(f"max_cases exceeded: {len(cases)} > {max_cases}")
    ids: set[str] = set()
    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise ValueError(f"case {index} must be an object")
        for field in ("id", "model", "request"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"case {index}: {field} must be a non-empty string")
        if "expect" in case and (
            not isinstance(case["expect"], list)
            or not case["expect"]
            or not all(isinstance(item, str) and item.strip() for item in case["expect"])
        ):
            raise ValueError(f"case {index}: expect must be a non-empty array of strings")
        if "contract" in case and not isinstance(case["contract"], dict):
            raise ValueError(f"case {index}: contract must be an object")
        if "rubric" in case:
            _validate_rubric(case["rubric"], index)
        if case["id"] in ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        ids.add(case["id"])

    case_results: list[dict[str, Any]] = []
    provider_calls = 0
    failures = 0
    metric_totals: dict[str, int | float] = {}
    quality_cases = 0
    quality_passed = 0
    latencies: list[int] = []
    trace_events = 0
    for case in cases:
        case_id = case.get("id")
        if mode == "PREVIEW" and not approve:
            case_results.append({"id": case_id, "status": "approval_required"})
            continue
        payload = {
            "id": case_id,
            "model": case.get("model"),
            "request": case.get("request"),
            "mode": mode,
        }
        if "expect" in case:
            payload["expect"] = case["expect"]
        if "contract" in case:
            payload["contract"] = case["contract"]
        if "rubric" in case:
            payload["rubric"] = case["rubric"]
        provider_calls += 1
        started = time.monotonic()
        try:
            response = provider(payload)
            raw_trace = response.get("trace") if isinstance(response, dict) else None
            trace = _unpack_trace(raw_trace)
            response, metrics = _unpack_provider_response(response)
            encoded_response = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
            response_bytes = len(encoded_response.encode("utf-8"))
            if response_bytes > max_response_bytes:
                raise ValueError(f"response exceeds {max_response_bytes} bytes")
        except Exception as exc:  # providers are external process/API boundaries
            failures += 1
            error = redact_sensitive(str(exc))
            if isinstance(exc, (TypeError, ValueError)) and "serializ" in error.lower():
                error = f"response is not JSON-serializable: {error}"
            duration_ms = max(0, round((time.monotonic() - started) * 1000))
            latencies.append(duration_ms)
            case_results.append({
                "id": case_id,
                "status": "failed",
                "error": error,
                "durationMs": duration_ms,
            })
            continue
        duration_ms = max(0, round((time.monotonic() - started) * 1000))
        latencies.append(duration_ms)
        result = {
            "id": case_id,
            "status": "measured",
            "response": redact_sensitive(response),
            "durationMs": duration_ms,
        }
        if metrics:
            result["metrics"] = redact_sensitive(metrics)
            for name, value in metrics.items():
                metric_totals[name] = metric_totals.get(name, 0) + value
        if trace:
            result["trace"] = trace
            trace_events += len(trace)
        if "expect" in case:
            result["quality"] = score_response(response, case["expect"], rubric=case.get("rubric"))
            quality_cases += 1
            quality_passed += int(result["quality"]["passed"])
        case_results.append(result)

    summary = {
        "cases": len(case_results),
        "measured": sum(item["status"] == "measured" for item in case_results),
        "approvalRequired": sum(item["status"] == "approval_required" for item in case_results),
        "failed": sum(item["status"] == "failed" for item in case_results),
    }
    report = {
        "schemaVersion": 1,
        "mode": mode,
        "providerCalls": provider_calls,
        "failures": failures,
        "caseResults": case_results,
        "summary": summary,
        "passed": failures == 0 and all(
            item.get("quality", {}).get("passed", True) for item in case_results
        ),
        "metrics": {
            "available": sorted(metric_totals),
            "total": metric_totals,
        },
        "quality": {
            "cases": len(case_results),
            "scored": quality_cases,
            "passed": quality_passed,
            "passRate": quality_passed / quality_cases if quality_cases else None,
        },
        "latency": {
            "measured": len(latencies),
            "p50Ms": _percentile(latencies, 0.50),
            "p95Ms": _percentile(latencies, 0.95),
        },
        "trace": {"events": trace_events},
    }
    if input_path is not None:
        report["input"] = {
            "format": "jsonl",
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        }
    report_errors = validate_report(report, "provider")
    if report_errors:
        raise RuntimeError("generated provider report violates its contract: " + "; ".join(report_errors))
    return report


def run_provider_matrix(
    cases: Iterable[dict[str, Any]],
    *,
    provider: Callable[[dict[str, Any]], Any],
    approve_preview: bool = False,
    input_path: Path | None = None,
    max_response_bytes: int = 1_048_576,
    max_cases: int = 1000,
) -> dict[str, Any]:
    """Run and join OFF, AUTO, and PREVIEW results by fixture ID."""
    cases = list(cases)
    mode_reports = {
        mode: run_provider_cases(
            cases,
            mode=mode,
            provider=provider,
            approve=approve_preview if mode == "PREVIEW" else False,
            input_path=input_path,
            max_response_bytes=max_response_bytes,
            max_cases=max_cases,
        )
        for mode in ("OFF", "AUTO", "PREVIEW")
    }
    joined = []
    for case in cases:
        case_id = case["id"]
        joined.append({
            "id": case_id,
            "results": {
                mode: next(item for item in report["caseResults"] if item["id"] == case_id)
                for mode, report in mode_reports.items()
            },
        })
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "mode": "matrix",
        "modes": ["OFF", "AUTO", "PREVIEW"],
        "providerCalls": sum(report["providerCalls"] for report in mode_reports.values()),
        "caseResults": joined,
        "runs": {mode: report["summary"] for mode, report in mode_reports.items()},
        "quality": {mode: report["quality"] for mode, report in mode_reports.items()},
        "metrics": {mode: report["metrics"] for mode, report in mode_reports.items()},
        "passed": all(report["passed"] for report in mode_reports.values()),
    }
    if input_path is not None:
        report["input"] = mode_reports["OFF"]["input"]
    report_errors = validate_report(report, "matrix")
    if report_errors:
        raise RuntimeError("generated matrix report violates its contract: " + "; ".join(report_errors))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opt-in provider evaluation cases")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--mode", choices=[*sorted(MODES), "MATRIX"], required=True)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--max-response-bytes", type=int, default=1_048_576)
    parser.add_argument("--max-cases", type=int, default=1000)
    parser.add_argument("--case", action="append", dest="selected_cases")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--provider", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if not args.provider:
        parser.error("--provider requires an executable argv")
    try:
        raw_input = args.cases.read_bytes()
        cases = []
        for line_number, line in enumerate(raw_input.decode("utf-8").splitlines(), 1):
            if line.strip():
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
        if args.selected_cases:
            for index, case in enumerate(cases, 1):
                if not isinstance(case, dict):
                    raise ValueError(f"case {index} must be an object")
            available_ids = {case.get("id") for case in cases}
            for case_id in args.selected_cases:
                if case_id not in available_ids:
                    raise ValueError(f"unknown case id: {case_id}")
            selected_ids = set(args.selected_cases)
            cases = [case for case in cases if case.get("id") in selected_ids]
        provider = lambda payload: cli_provider(
            args.provider,
            payload,
            timeout=args.timeout,
            max_output_bytes=args.max_response_bytes,
        )
        if args.mode == "MATRIX":
            result = run_provider_matrix(
                cases,
                provider=provider,
                approve_preview=args.approve,
                input_path=args.cases,
                max_response_bytes=args.max_response_bytes,
                max_cases=args.max_cases,
            )
        else:
            result = run_provider_cases(
                cases,
                mode=args.mode,
                approve=args.approve,
                input_path=args.cases,
                max_response_bytes=args.max_response_bytes,
                max_cases=args.max_cases,
                provider=provider,
            )
        result["selection"] = {
            "requested": args.selected_cases or [],
            "selected": len(cases),
        }
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        if args.mode == "MATRIX":
            result = {
                "schemaVersion": 1,
                "mode": "matrix",
                "modes": ["OFF", "AUTO", "PREVIEW"],
                "providerCalls": 0,
                "caseResults": [],
                "runs": {},
                "errors": [redact_sensitive(str(exc))],
                "selection": {"requested": args.selected_cases or [], "selected": 0},
                "input": {
                    "format": "jsonl",
                    "sha256": hashlib.sha256(raw_input).hexdigest() if "raw_input" in locals() else None,
                },
                "passed": False,
            }
        else:
            result = {
                "schemaVersion": 1,
                "mode": args.mode,
                "providerCalls": 0,
                "failures": 0,
                "caseResults": [],
                "summary": {"cases": 0, "measured": 0, "approvalRequired": 0, "failed": 0},
                "errors": [redact_sensitive(str(exc))],
                "selection": {"requested": args.selected_cases or [], "selected": 0},
                "input": {
                    "format": "jsonl",
                    "sha256": hashlib.sha256(raw_input).hexdigest() if "raw_input" in locals() else None,
                },
                "passed": False,
            }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output.parent, delete=False
        ) as temporary:
            temporary.write(rendered)
            temporary_path = Path(temporary.name)
        temporary_path.replace(args.output)
    sys.stdout.buffer.write(rendered.encode("utf-8"))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
