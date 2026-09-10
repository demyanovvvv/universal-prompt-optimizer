#!/usr/bin/env python3
"""Keep model registry, skills, commands, and native routing tables aligned."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".agents/skills/prompt-optimizer/references/model-registry.json"
SKILLS = ROOT / ".agents/skills"
REFERENCES = SKILLS / "prompt-optimizer/references"
OPENCode = ROOT / "adapters/opencode/plugin/index.ts"
PI = ROOT / "adapters/pi/extensions/prompt-optimizer.ts"
CANONICAL_SKILL = SKILLS / "prompt-optimizer/SKILL.md"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def check() -> list[str]:
    errors: list[str] = []
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if data.get("version") != VERSION:
        errors.append(f"registry version {data.get('version')!r} does not match VERSION {VERSION!r}")
    profiles = data.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        return ["registry profiles must be a non-empty array"]

    ids = [item.get("id") for item in profiles]
    if len(ids) != len(set(ids)):
        errors.append("registry contains duplicate profile IDs")
    aliases: dict[str, str] = {}
    for item in profiles:
        profile_id = item.get("id")
        if not isinstance(profile_id, str):
            errors.append(f"profile has invalid id: {profile_id!r}")
            continue
        profile_file = item.get("file")
        if not isinstance(profile_file, str) or not (REFERENCES / profile_file).is_file():
            errors.append(f"{profile_id}: missing profile reference {profile_file!r}")
        else:
            text = (REFERENCES / profile_file).read_text(encoding="utf-8")
            if "Provenance" not in text or "Official source" not in text and "Official sources" not in text:
                errors.append(f"{profile_id}: profile is missing provenance/source")
        skill_name = f"prompt-{profile_id.replace('.', '-') }"
        skill = SKILLS / skill_name / "SKILL.md"
        if not skill.is_file():
            errors.append(f"{profile_id}: missing manual override skill {skill_name}")
        else:
            skill_text = skill.read_text(encoding="utf-8")
            if f'version: "{VERSION}"' not in skill_text:
                errors.append(f"{profile_id}: manual skill version is not {VERSION}")
        command = ROOT / "adapters/opencode/commands" / f"{skill_name}.md"
        if not command.is_file():
            errors.append(f"{profile_id}: missing OpenCode command {command.name}")
        profile_aliases = item.get("aliases", [])
        if not isinstance(profile_aliases, list) or not profile_aliases:
            errors.append(f"{profile_id}: aliases must be a non-empty array")
            profile_aliases = []
        for alias in [profile_id, *profile_aliases]:
            if not isinstance(alias, str):
                errors.append(f"{profile_id}: invalid alias {alias!r}")
                continue
            key = normal(alias)
            previous = aliases.get(key)
            if previous and previous != profile_id:
                errors.append(f"ambiguous normalized alias {alias!r}: {previous} and {profile_id}")
            aliases[key] = profile_id

    opencode = OPENCode.read_text(encoding="utf-8")
    type_block = opencode.split("type Profile =", 1)[1].split("type Settings", 1)[0]
    routed = set(re.findall(r'"([^"]+)"', type_block))
    registry_ids = set(ids)
    if routed != registry_ids:
        errors.append(
            "OpenCode Profile union mismatch: "
            f"missing={sorted(registry_ids - routed)} extra={sorted(routed - registry_ids)}"
        )
    hint_block = opencode.split("const PROFILE_HINTS:", 1)[1].split("\n}\n", 1)[0]
    hinted = set(re.findall(r'^\s*"([^"\n]+)":', hint_block, re.MULTILINE))
    hinted.update(re.findall(r'^\s*([a-z][a-z0-9-]*):', hint_block, re.MULTILINE))
    if hinted != registry_ids:
        errors.append(
            "OpenCode PROFILE_HINTS mismatch: "
            f"missing={sorted(registry_ids - hinted)} extra={sorted(hinted - registry_ids)}"
        )

    pi_lower = PI.read_text(encoding="utf-8").lower()
    for profile_id in registry_ids:
        # Pi deliberately uses regexes instead of a generated exact map. Require
        # every provider/model token to remain represented in that routing table.
        tokens = [token for token in normal(profile_id).split("-") if len(token) > 2]
        if not tokens or not all(token in pi_lower for token in tokens):
            errors.append(f"{profile_id}: Pi routing table no longer contains its model tokens")

    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    for profile_id in registry_ids:
        if profile_id not in canonical and profile_id.replace(".", "-") not in canonical:
            errors.append(f"{profile_id}: canonical skill list is missing profile")
    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Registry conformance passed: {len(json.loads(REGISTRY.read_text(encoding='utf-8'))['profiles'])} profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
