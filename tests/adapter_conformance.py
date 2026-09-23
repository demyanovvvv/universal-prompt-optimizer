#!/usr/bin/env python3
"""Keep the adapter capability matrix aligned with the shipped adapters.

The matrix is the machine-readable contract behind COMPATIBILITY.md. This
checker fails when an adapter is added, removed, or renamed without updating the
matrix, and when a documented behavior claim drifts from the adapter artifacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "adapters/capability-matrix.json"
COMPATIBILITY = ROOT / "COMPATIBILITY.md"
INSTALL = ROOT / "install.py"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

BEHAVIORS = {"AUTO", "PREVIEW", "OFF"}
PREVIEW_ENFORCEMENT = {"advisory", "host-tool", "host-enforced"}
FIRST_TURN = {"exact", "family", "configured-or-neutral"}
QUALITY_GATE = {"native", "runtime-state", "instructions"}
SESSION_STATE = {"process-local", "file", "none"}


def _install_agents() -> set[str]:
    match = re.search(r"^AGENTS\s*=\s*\{([^}]*)\}", INSTALL.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        return set()
    return {item.strip().strip("\"'") for item in match.group(1).split(",") if item.strip()}


def _compatibility_names() -> set[str]:
    names: set[str] = set()
    for line in COMPATIBILITY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Agent"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            names.add(cells[0])
    return names


def check() -> list[str]:
    errors: list[str] = []
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1:
        errors.append("capability matrix schemaVersion must be 1")
    if data.get("version") != VERSION:
        errors.append(f"capability matrix version {data.get('version')!r} does not match VERSION {VERSION!r}")
    adapters = data.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        return ["capability matrix adapters must be a non-empty array"]

    ids = [item.get("id") for item in adapters]
    if len(ids) != len(set(ids)):
        errors.append("capability matrix contains duplicate adapter IDs")

    expected_ids = _install_agents()
    if expected_ids and set(ids) != expected_ids:
        missing = sorted(expected_ids - set(ids))
        extra = sorted(set(ids) - expected_ids)
        errors.append(f"capability matrix adapter IDs do not match installer AGENTS: missing={missing} extra={extra}")

    for item in adapters:
        adapter_id = item.get("id")
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            errors.append(f"adapter has invalid id: {adapter_id!r}")
            continue
        for field in ("name", "mechanism", "firstTurnRouting", "previewEnforcement", "qualityGateSupport", "sessionState"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{adapter_id}: {field} must be a non-empty string")
        behaviors = item.get("behaviors")
        if not isinstance(behaviors, list) or set(behaviors) != BEHAVIORS:
            errors.append(f"{adapter_id}: behaviors must be exactly {sorted(BEHAVIORS)}")
        if item.get("previewEnforcement") not in PREVIEW_ENFORCEMENT:
            errors.append(f"{adapter_id}: previewEnforcement must be one of {sorted(PREVIEW_ENFORCEMENT)}")
        if item.get("firstTurnRouting") not in FIRST_TURN:
            errors.append(f"{adapter_id}: firstTurnRouting must be one of {sorted(FIRST_TURN)}")
        if item.get("qualityGateSupport") not in QUALITY_GATE:
            errors.append(f"{adapter_id}: qualityGateSupport must be one of {sorted(QUALITY_GATE)}")
        if item.get("sessionState") not in SESSION_STATE:
            errors.append(f"{adapter_id}: sessionState must be one of {sorted(SESSION_STATE)}")
        if not isinstance(item.get("sharedSkills"), bool):
            errors.append(f"{adapter_id}: sharedSkills must be a boolean")
        if not isinstance(item.get("exactModelRouting"), bool):
            errors.append(f"{adapter_id}: exactModelRouting must be a boolean")
        if not isinstance(item.get("hostEnforcedApproval"), bool):
            errors.append(f"{adapter_id}: hostEnforcedApproval must be a boolean")
        limitations = item.get("knownLimitations")
        if not isinstance(limitations, list) or not limitations or not all(isinstance(entry, str) and entry.strip() for entry in limitations):
            errors.append(f"{adapter_id}: knownLimitations must be a non-empty array of strings")
        if item.get("hostEnforcedApproval") and item.get("previewEnforcement") != "host-enforced":
            errors.append(f"{adapter_id}: hostEnforcedApproval requires previewEnforcement=host-enforced")

    documented = _compatibility_names()
    matrix_names = {item.get("name") for item in adapters}
    if documented and matrix_names != documented:
        errors.append(
            "capability matrix names do not match COMPATIBILITY.md: "
            f"missing={sorted(matrix_names - documented)} extra={sorted(documented - matrix_names)}"
        )
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
