#!/usr/bin/env python3
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

STATE_TTL_SECONDS = 30 * 24 * 60 * 60
STATE_LIMIT = 200
QUALITY_GATES = {"pass", "light", "full", "adaptive"}


def normalize_quality_gate(value):
    if isinstance(value, bool):
        return "adaptive" if value else "pass"
    return value if isinstance(value, str) and value in QUALITY_GATES else None

def read_json(path: Path, default):
    try:
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else default
    except Exception:
        pass
    return default


def config(cwd: Path):
    d = {"behavior": "auto", "scope": "all", "qualityGate": "adaptive", "unsupportedModel": "generic"}
    invalid_config = False
    for p in [Path.home() / ".config/prompt-optimizer/config.json", cwd / ".prompt-optimizer.json"]:
        if not p.exists():
            continue
        try:
            value = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            invalid_config = True
            continue
        if not isinstance(value, dict):
            invalid_config = True
            continue
        if (
            ("schemaVersion" in value and (not isinstance(value["schemaVersion"], int) or isinstance(value["schemaVersion"], bool) or value["schemaVersion"] != 1))
            or ("behavior" in value and (not isinstance(value["behavior"], str) or value["behavior"] not in {"auto", "preview", "off"}))
            or ("scope" in value and (not isinstance(value["scope"], str) or value["scope"] not in {"first", "all"}))
            or ("qualityGate" in value and normalize_quality_gate(value["qualityGate"]) is None)
            or ("unsupportedModel" in value and (not isinstance(value["unsupportedModel"], str) or value["unsupportedModel"] not in {"skip", "generic"}))
        ):
            invalid_config = True
            continue
        if value.get("behavior") in {"auto", "preview", "off"}:
            d["behavior"] = value["behavior"]
        if value.get("scope") in {"first", "all"}:
            d["scope"] = value["scope"]
        quality_gate = normalize_quality_gate(value.get("qualityGate"))
        if quality_gate is not None:
            d["qualityGate"] = quality_gate
        if value.get("unsupportedModel") in {"skip", "generic"}:
            d["unsupportedModel"] = value["unsupportedModel"]
    if invalid_config:
        d["behavior"] = "off"
    return d


def state_path(cwd: Path) -> Path:
    return cwd / ".gemini/.prompt-optimizer-model-state.json"


@contextmanager
def state_lock(path: Path):
    """Serialize state read-modify-write across concurrent hook processes."""
    lock = path.with_name(path.name + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5
    acquired = False
    while time.monotonic() < deadline:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 30:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            time.sleep(0.02)
    if not acquired:
        raise TimeoutError(f"Timed out waiting for state lock: {path}")
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def write_json_atomic(path: Path, value: dict) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def read_model_state(cwd: Path) -> dict:
    return read_json(state_path(cwd), {})


def prune_state(state: dict) -> dict:
    cutoff = time.time() - STATE_TTL_SECONDS
    fresh = {}
    for key, value in state.items():
        if isinstance(value, dict):
            updated_at = value.get("updatedAt")
            if isinstance(updated_at, (int, float)) and updated_at < cutoff:
                continue
        fresh[key] = value
    if len(fresh) > STATE_LIMIT:
        ranked = sorted(
            fresh.items(),
            key=lambda item: item[1].get("updatedAt", 0) if isinstance(item[1], dict) else 0,
            reverse=True,
        )
        fresh = dict(ranked[: STATE_LIMIT // 2])
    return fresh


def remember_model(cwd: Path, session: str | None, model: str | None) -> None:
    if not session or not model:
        return
    try:
        path = state_path(cwd)
        with state_lock(path):
            state = prune_state(read_model_state(cwd))
            state[str(session)] = {"model": str(model), "updatedAt": int(time.time())}
            write_json_atomic(path, state)
    except Exception:
        pass


def observed_model(cwd: Path, session: str | None) -> str | None:
    if not session:
        return None
    value = read_model_state(cwd).get(str(session))
    if isinstance(value, dict):
        updated_at = value.get("updatedAt")
        if isinstance(updated_at, (int, float)) and updated_at < time.time() - STATE_TTL_SECONDS:
            return None
        value = value.get("model")
    return str(value) if isinstance(value, str) and value.strip() else None


def configured_model(cwd: Path) -> str | None:
    # Gemini CLI precedence relevant to what a hook can observe before the first
    # model call: environment > project settings > user settings. A CLI --model
    # argument has higher precedence but is not exposed to BeforeAgent, so we do
    # not pretend to know it until BeforeModel reports the resolved model.
    env_model = os.environ.get("GEMINI_MODEL", "").strip()
    if env_model:
        return env_model
    for path in [cwd / ".gemini/settings.json", Path.home() / ".gemini/settings.json"]:
        data = read_json(path, {})
        model = data.get("model")
        if isinstance(model, dict):
            name = model.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def exact_profile_for(model: str | None) -> str | None:
    if not model:
        return None
    mid = model.lower().replace("_", "-")
    leaf = mid.rsplit("/", 1)[-1]
    if leaf.endswith("-latest"):
        leaf = leaf[:-7]
    profiles = {
        "gpt-6-astra": "astra",
        "astra": "astra",
        "gpt-6-sol": "sol",
        "sol": "sol",
        "gpt-6.1-sol": "gpt-6.1-sol",
        "gpt-5.6-terra": "terra",
        "terra": "terra",
        "gpt-6-luna": "luna",
        "luna": "luna",
        "gpt-5.6": "gpt-5.6-sol",
        "gpt-5.6-sol": "gpt-5.6-sol",
        "gpt-5.6-luna": "gpt-5.6-luna",
        "glm-5.2": "glm-5.2",
        "glm-5-2": "glm-5.2",
        "glm-5.3": "glm-5.3",
        "glm-5-3": "glm-5.3",
        "glm-5.3-flash": "glm-5.3-flash",
        "glm-5-3-flash": "glm-5.3-flash",
        "deepseek-v4.1-flash": "deepseek-v4.1-flash",
        "deepseek-v4-1-flash": "deepseek-v4.1-flash",
        "deepseek-flash": "deepseek-v4.1-flash",
        "deepseek-v4-flash": "deepseek-v4-flash",
        "deepseek-v4-flash-0731": "deepseek-v4-flash",
        "deepseek-v4-pro": "deepseek-v4-pro",
        "claude-fable-5.1": "claude-fable-5.1",
        "claude-fable-5-1": "claude-fable-5.1",
        "claude-fable-5": "claude-fable-5",
        "claude-opus-5.5": "claude-opus-5.5",
        "claude-opus-5-5": "claude-opus-5.5",
        "claude-opus-5": "claude-opus-5",
        "claude-opus-4.8": "claude-opus-4.8",
        "claude-opus-4-8": "claude-opus-4.8",
        "claude-sonnet-5": "claude-sonnet-5",
        "claude-sonnet-5.5": "claude-sonnet-5.5",
        "claude-sonnet-5-5": "claude-sonnet-5.5",
        "kimi-k3": "kimi-k3",
        "muse-spark-1.3": "muse-spark-1.3",
        "muse-spark-1-3": "muse-spark-1.3",
        "hy4-preview": "hy4-preview",
        "hy-4-preview": "hy4-preview",
        "qwen3.8-max": "qwen3.8-max",
        "qwen3.8-max-0902": "qwen3.8-max",
        "qwen3.8-max-2026-09-02": "qwen3.8-max",
        "gemini-3.8-flash": "gemini-3.8-flash",
        "grok-4.6": "grok-4.6"
    }
    if leaf in profiles:
        return profiles[leaf]
    return None


def first_scope_active(inp: dict, cwd: Path, cfg: dict) -> bool:
    if cfg.get("scope") != "first":
        return True
    session = inp.get("session_id") or inp.get("sessionId")
    if not session:
        # Do not invent session identity. Applying the preflight is safer than
        # silently skipping a user's first request on an unknown schema.
        return True
    turn_state_path = cwd / ".gemini/.prompt-optimizer-session-state.json"
    key = str(session)
    try:
        with state_lock(turn_state_path):
            state = prune_state(read_json(turn_state_path, {}))
            if key in state:
                return False
            state[key] = {"updatedAt": int(time.time())}
            write_json_atomic(turn_state_path, state)
    except Exception:
        # If state cannot be locked or persisted, do not silently suppress the
        # user's first eligible request.
        return True
    return True


def silent_output(event: str) -> dict:
    # BeforeModel does not need hookSpecificOutput when no request fields are
    # overridden. Returning only suppressOutput leaves the original request intact.
    if event == "BeforeAgent":
        return {"suppressOutput": True, "hookSpecificOutput": {"additionalContext": ""}}
    return {"suppressOutput": True}


inp = json.load(sys.stdin)
cwd = Path(inp.get("cwd") or os.environ.get("GEMINI_PROJECT_DIR") or os.getcwd())
event = str(inp.get("hook_event_name") or "BeforeAgent")
session = inp.get("session_id") or inp.get("sessionId")
cfg = config(cwd)

if cfg.get("behavior") == "off":
    print(json.dumps(silent_output(event)))
    raise SystemExit

# BeforeModel is observation-only: capture the resolved model and never rewrite,
# replace, or reconstruct the outgoing request.
if event == "BeforeModel":
    request = inp.get("llm_request")
    if isinstance(request, dict):
        model = request.get("model")
        if isinstance(model, str) and model.strip():
            remember_model(cwd, str(session) if session else None, model.strip())
    print(json.dumps(silent_output(event)))
    raise SystemExit

common = (
    "Preserve intent, exact literals, hard constraints, project rules, required verification and approval boundaries; "
    "do not invent requirements. Keep the execution brief as concise as the active model permits. Native Reasoning First: "
    "never request hidden chain-of-thought or add generic think-step-by-step scaffolding. User instructions override this preflight. "
)
quality_gate = cfg.get("qualityGate", "adaptive")
if quality_gate == "pass":
    base = "Prompt Optimizer v5.12. Quality gate is disabled: normalize every in-scope request into the leanest model-appropriate execution brief before acting. " + common
elif quality_gate == "light":
    base = "Prompt Optimizer v5.12. Selected quality gate: LIGHT. Add only a missing high-value boundary, constraint, done criterion, approval boundary, or output shape before acting. " + common
elif quality_gate == "full":
    base = "Prompt Optimizer v5.12. Selected quality gate: FULL. Build a concise execution brief from only task-relevant context before acting. " + common
else:
    base = "Prompt Optimizer v5.12. Apply PASS/LIGHT/FULL quality gating before acting. " + common

# Prefer the exact model observed by BeforeModel in this session. Before the first
# model call, use only explicit configuration visible to the hook. Never assume a
# model from the agent name itself.
model = observed_model(cwd, str(session) if session else None) or configured_model(cwd)
profile = exact_profile_for(model)

# Keep SKIP semantics consistent with OpenCode/Pi: if there is no exact supported
# profile, do not inject the optimizer at all. GENERIC explicitly opts into the
# neutral model-agnostic preflight.
if profile is None and cfg.get("unsupportedModel") != "generic":
    print(json.dumps(silent_output("BeforeAgent")))
    raise SystemExit

# Consume the first-turn slot only after this turn is eligible. An unknown
# model with SKIP must not prevent a later, observable supported model turn.
if not first_scope_active(inp, cwd, cfg):
    print(json.dumps(silent_output("BeforeAgent")))
    raise SystemExit

if profile == "gemini-3.8-flash":
    base += (
        "Resolved model profile: Gemini 3.8 Flash. Prefer concise direct instructions and aggressively PASS/LIGHT. "
        "For long context put source data first and the specific task at the end; avoid verbose legacy prompt frameworks. "
    )
elif profile == "gpt-6.1-sol":
    base += "Resolved model profile: GPT-6.1 Sol. Preserve decisive context, scope, approval boundaries and observable completion; continue authorized work through relevant validation, use bounded current evidence, and keep reasoning effort in runtime rather than prompt text. "
elif profile == "sol":
    base += "Resolved model profile: GPT-6 Sol. Preserve decisive context, hard constraints, approval boundaries and observable completion; follow through on authorized work with proportionate validation. "
elif profile == "claude-sonnet-5.5":
    base += "Resolved model profile: Claude Sonnet 5.5. Use a bounded objective, scope, initiative boundary, deliverable and verification; continue authorized work without premature check-ins, batch independent tools, and report completed versus verified versus unconfirmed work. "
elif profile in {"claude-sonnet-5", "claude-opus-5.5", "claude-opus-5", "claude-opus-4.8", "claude-fable-5.1", "claude-fable-5"}:
    base += f"Resolved Claude profile: {profile}. Use clear scope, concrete completion criteria, relevant tool evidence and behavior verification; use examples/XML and long-context source ordering only when they materially clarify the task. Keep effort and thinking in runtime. "
elif profile:
    base += f"Resolved model profile: {profile}. Apply only its matching profile from the installed prompt-optimizer skill; preserve scope, constraints and required verification. "
elif model:
    base += f"Observed/configured model: {model}. No exact installed model profile matches it; use the neutral model-agnostic optimizer profile and do not invent model-specific behavior. "
else:
    base += "The exact active model is not yet observable on this turn; use only the neutral model-agnostic optimizer profile. Do not guess a model family or variant. "

if cfg.get("behavior") == "preview":
    base += (
        "PREVIEW MODE: before mutating/external work, form the exact optimized execution prompt and call the built-in ask_user tool once with a choice/yes-no approval. "
        "Show the exact prompt, put Выполнить first/default and allow modification/custom text. After approval execute without re-previewing. "
        "If ask_user is unavailable, print the prompt and wait for explicit confirmation. "
    )
else:
    if quality_gate == "pass":
        base += "AUTO MODE: normalize every in-scope prompt and execute in the same turn. "
    elif quality_gate == "light":
        base += "AUTO MODE: apply the selected LIGHT gate and execute in the same turn. "
    elif quality_gate == "full":
        base += "AUTO MODE: apply the selected FULL gate and execute in the same turn. "
    else:
        base += "AUTO MODE: silently optimize only when useful and execute in the same turn. "

print(json.dumps({"suppressOutput": True, "hookSpecificOutput": {"additionalContext": base}}))
