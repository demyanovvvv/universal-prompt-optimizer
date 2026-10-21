#!/usr/bin/env python3
"""Run deterministic evaluation-fixture checks without requiring an LLM API.

The repository intentionally keeps provider calls out of CI. This runner checks
that every case has a resolvable model contract, useful expectations, and the
negative cases needed to prevent unsafe routing regressions. A future provider
runner can consume the same JSONL schema and add measured OFF/AUTO/PREVIEW
results beside this static result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from evals.report_schema import validate_report
except ModuleNotFoundError:  # supports the documented `python evals/run.py` form
    from report_schema import validate_report


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals/cases.jsonl"
REGISTRY = ROOT / ".agents/skills/prompt-optimizer/references/model-registry.json"


def load_cases(path: Path) -> list[dict]:
    cases: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: case must be an object")
        cases.append(value)
    return cases


def run(path: Path = CASES, strict_coverage: bool = False) -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    known_models = {item["id"] for item in registry["profiles"]}
    known_aliases = {alias for item in registry["profiles"] for alias in [item["id"], *item.get("aliases", [])]}
    errors: list[str] = []
    case_results: list[dict] = []
    ids: set[str] = set()
    contracts = 0
    required_fields = {"id", "model", "request", "expect"}
    contract_fields = {
        "profile": (str, type(None)),
        "taskType": str,
        "risk": str,
        "executionIntent": str,
        "gate": str,
        "action": str,
    }
    contract_values = {
        "profile": known_models | {None},
        "taskType": {
            "implementation", "bugfix", "refactor", "review", "research",
            "documentation", "testing", "planning", "security", "migration",
            "unknown",
        },
        "risk": {"none", "consequential"},
        "executionIntent": {"execute", "plan", "review", "explain"},
        "gate": {"pass", "light", "full"},
        "action": {"apply", "preview", "skip"},
    }
    contract_field_counts = {field: 0 for field in contract_fields}
    contract_value_counts = {field: {} for field in contract_fields}
    try:
        input_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        input_digest = None
    report_metadata = {
        "schemaVersion": 1,
        "mode": "deterministic",
        "providerCalls": 0,
        "strictCoverage": strict_coverage,
        "input": {"format": "jsonl", "sha256": input_digest},
    }
    try:
        cases = load_cases(path)
    except (OSError, ValueError) as exc:
        return {
            **report_metadata,
            "cases": 0,
            "contracts": 0,
            "coverage": {
                "total": 0,
                "fields": contract_field_counts,
                "values": contract_value_counts,
            },
            "caseResults": [],
            "errors": [str(exc)],
            "passed": False,
        }
    for index, case in enumerate(cases, 1):
        case_error_start = len(errors)
        missing = required_fields - set(case)
        if missing:
            errors.append(f"case {index}: missing fields {sorted(missing)}")
            case_results.append({
                "id": case.get("id", f"case-{index}"),
                "passed": False,
                "errors": errors[case_error_start:],
            })
            continue
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip() or case_id in ids:
            errors.append(f"case {index}: id must be unique and non-empty")
            case_label = f"case {index}"
        else:
            ids.add(case_id)
            case_label = case_id
        if not isinstance(case["request"], str) or not case["request"].strip():
            errors.append(f"{case_label}: request must be non-empty")
        if not isinstance(case["expect"], list) or not case["expect"]:
            errors.append(f"{case_label}: expect must be a non-empty array")
        rubric = case.get("rubric")
        if rubric is not None:
            if not isinstance(rubric, dict):
                errors.append(f"{case_label}: rubric must be an object")
            else:
                forbidden = rubric.get("forbidden", [])
                if not isinstance(forbidden, list) or not all(isinstance(item, str) and item.strip() for item in forbidden):
                    errors.append(f"{case_label}: rubric.forbidden must be an array of non-empty strings")
                min_score = rubric.get("minScore", 1.0)
                if not isinstance(min_score, (int, float)) or isinstance(min_score, bool) or not math.isfinite(min_score) or not 0 <= min_score <= 1:
                    errors.append(f"{case_label}: rubric.minScore must be finite and between 0 and 1")
                required_rubric_fields = rubric.get("requiredFields", [])
                if not isinstance(required_rubric_fields, list) or not all(isinstance(item, str) and item.strip() for item in required_rubric_fields):
                    errors.append(f"{case_label}: rubric.requiredFields must be an array of non-empty strings")
                if "exact" in rubric and not isinstance(rubric["exact"], (dict, list, str, int, float, bool, type(None))):
                    errors.append(f"{case_label}: rubric.exact must be JSON-compatible")
        contract = case.get("contract")
        if contract is not None:
            contracts += 1
            if not isinstance(contract, dict):
                errors.append(f"{case_label}: contract must be an object")
            else:
                for field, value in contract.items():
                    if field not in contract_fields:
                        errors.append(f"{case_label}: unknown contract field: {field}")
                        continue
                    if not isinstance(value, contract_fields[field]):
                        errors.append(f"{case_label}: contract.{field} has invalid type")
                        continue
                    if field in contract_values and value not in contract_values[field]:
                        errors.append(f"{case_label}: contract.{field} has invalid value: {value}")
                    contract_field_counts[field] += 1
                    value_key = "null" if value is None else str(value)
                    field_counts = contract_value_counts[field]
                    field_counts[value_key] = field_counts.get(value_key, 0) + 1
        model = case["model"]
        if not isinstance(model, str) or not model.strip():
            errors.append(f"{case_label}: model must be a non-empty string")
        elif model not in known_models and model not in known_aliases and model not in {"deepseek-v4", "gpt-6", "deepseek-v4.1", "deepseek-v4.10-flash", "deepseek-v4-flash-extra", "gemini-4-argon-extra"}:
            errors.append(f"{case_label}: model is not in registry or explicit ambiguous-model set: {model}")
        elif model == "deepseek-v4" and not any("guess" in str(item).lower() or "flash" in str(item).lower() for item in case["expect"]):
            errors.append(f"{case_label}: ambiguous DeepSeek case must assert no variant guess")
        elif model == "gpt-6" and not any("never guess" in str(item).lower() or "no variant guess" in str(item).lower() for item in case["expect"]):
            errors.append(f"{case_label}: ambiguous GPT-6 case must assert no variant guess")

        case_results.append({
            "id": case_id,
            "passed": len(errors) == case_error_start,
            "errors": errors[case_error_start:],
        })

    case_ids = ids
    required_negative_cases = {
        "negative-ambiguous-model",
        "negative-prompt-injection",
        "negative-destructive-action",
        "negative-secret-preservation",
    }
    missing_negative = required_negative_cases - case_ids
    if missing_negative:
        errors.append(f"missing negative evaluation cases: {sorted(missing_negative)}")
    required_astra_cases = {
        "astra-pass-zero-context",
        "astra-completion-boundary",
        "astra-no-needless-approval",
        "astra-plan-boundary",
        "astra-skill-progressive-disclosure",
    }
    missing_astra = required_astra_cases - case_ids
    if missing_astra:
        errors.append(f"missing GPT-6 Astra evaluation cases: {sorted(missing_astra)}")
    coverage = {
        "total": contracts,
        "fields": contract_field_counts,
        "values": contract_value_counts,
    }
    if strict_coverage:
        required_coverage = {
            "risk": "consequential",
            "gate": "full",
            "action": "skip",
        }
        for field, value in required_coverage.items():
            if coverage["values"].get(field, {}).get(value, 0) == 0:
                errors.append(f"strict coverage missing contract.{field}={value}")
    report = {
        **report_metadata,
        "cases": len(cases),
        "contracts": contracts,
        "coverage": coverage,
        "caseResults": case_results,
        "errors": errors,
        "passed": not errors,
    }
    report_errors = validate_report(report, "deterministic")
    if report_errors:
        report["errors"].extend(report_errors)
        report["passed"] = False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Prompt Optimizer evaluation checks")
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict-coverage", action="store_true", help="require consequential, FULL, and skip contract coverage")
    args = parser.parse_args()
    result = run(args.cases, strict_coverage=args.strict_coverage)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
