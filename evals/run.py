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
import json
from pathlib import Path


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


def run(path: Path = CASES) -> dict:
    cases = load_cases(path)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    known_models = {item["id"] for item in registry["profiles"]}
    known_aliases = {alias for item in registry["profiles"] for alias in [item["id"], *item.get("aliases", [])]}
    errors: list[str] = []
    ids: set[str] = set()
    required_fields = {"id", "model", "request", "expect"}
    for index, case in enumerate(cases, 1):
        missing = required_fields - set(case)
        if missing:
            errors.append(f"case {index}: missing fields {sorted(missing)}")
            continue
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip() or case_id in ids:
            errors.append(f"case {index}: id must be unique and non-empty")
        ids.add(case_id)
        if not isinstance(case["request"], str) or not case["request"].strip():
            errors.append(f"{case_id}: request must be non-empty")
        if not isinstance(case["expect"], list) or not case["expect"]:
            errors.append(f"{case_id}: expect must be a non-empty array")
        model = case["model"]
        if model not in known_models and model not in known_aliases and model not in {"deepseek-v4"}:
            errors.append(f"{case_id}: model is not in registry or explicit ambiguous-model set: {model}")
        if model == "deepseek-v4" and not any("guess" in str(item).lower() or "flash" in str(item).lower() for item in case["expect"]):
            errors.append(f"{case_id}: ambiguous DeepSeek case must assert no variant guess")

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
    return {"cases": len(cases), "errors": errors, "passed": not errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Prompt Optimizer evaluation checks")
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.cases)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
