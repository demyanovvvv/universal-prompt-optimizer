"""Opt-in provider harness for measured OFF/AUTO/PREVIEW fixture runs.

The provider is deliberately injected by the caller. This module never reads
credentials, performs network requests, or pretends to evaluate a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from evals.quality import score_response


MODES = {"OFF", "AUTO", "PREVIEW"}


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
        if case["id"] in ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        ids.add(case["id"])

    case_results: list[dict[str, Any]] = []
    provider_calls = 0
    failures = 0
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
        provider_calls += 1
        started = time.monotonic()
        try:
            response = provider(payload)
            encoded_response = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
            response_bytes = len(encoded_response.encode("utf-8"))
            if response_bytes > max_response_bytes:
                raise ValueError(f"response exceeds {max_response_bytes} bytes")
        except Exception as exc:  # providers are external process/API boundaries
            failures += 1
            error = str(exc)
            if isinstance(exc, (TypeError, ValueError)) and "serializ" in error.lower():
                error = f"response is not JSON-serializable: {error}"
            case_results.append({
                "id": case_id,
                "status": "failed",
                "error": error,
                "durationMs": max(0, round((time.monotonic() - started) * 1000)),
            })
            continue
        result = {
            "id": case_id,
            "status": "measured",
            "response": response,
            "durationMs": max(0, round((time.monotonic() - started) * 1000)),
        }
        if "expect" in case:
            result["quality"] = score_response(response, case["expect"])
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
    }
    if input_path is not None:
        report["input"] = {
            "format": "jsonl",
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        }
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
        "passed": all(report["passed"] for report in mode_reports.values()),
    }
    if input_path is not None:
        report["input"] = mode_reports["OFF"]["input"]
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
        result = {
            "schemaVersion": 1,
            "mode": args.mode,
            "providerCalls": 0,
            "failures": 0,
            "caseResults": [],
            "summary": {
                "cases": 0,
                "measured": 0,
                "approvalRequired": 0,
                "failed": 0,
            },
            "errors": [str(exc)],
            "selection": {
                "requested": args.selected_cases or [],
                "selected": 0,
            },
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
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
