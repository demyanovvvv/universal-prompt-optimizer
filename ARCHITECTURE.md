# Architecture

## System overview

Universal Prompt Optimizer is an adaptive, model-aware preflight layer for coding-agent hosts. It preserves user intent and constraints, applies useful model guidance within the host's existing turn, and requires no separate optimizer LLM call. It combines a canonical prompt-optimization skill, model profiles, host adapters, an installer, and deterministic/evaluation verification. Preflight is local; the host's normal model calls remain subject to its own configuration.

The main boundaries are:

```text
Canonical model/profile data
        ↓ generated routing artifacts
Prompt optimizer skill and profile rules
        ↓ host-specific integration
Adapters and OpenCode runtime
        ↓ installation/configuration
Installer and lifecycle transactions
        ↓ verification
Unit, conformance, runtime, and evaluation tests
```

Changes should move through these boundaries in the direction shown above. A downstream generated artifact must not become a new source of truth.

## Source-of-truth map

| Concern | Canonical source | Derived or consuming locations |
|---|---|---|
| Supported adapters | `adapters/manifest.json` | installer, conformance tests, compatibility docs |
| Model routing and profiles | `.agents/skills/prompt-optimizer/references/model-registry.json` and matching reference profiles | generated OpenCode routing data, Pi routing data, adapter behavior |
| Managed configuration contract | `config_contract.py` | `adapters/opencode/plugin/config-contract.ts` and adapter implementations |
| Cross-platform verification | `tools/selfcheck.py` | `verify.mjs`, `verify.sh` launchers |
| Evaluation cases and baselines | `evals/cases.jsonl`, `evals/baselines/` | evaluation reports and regression gates |

When a canonical source changes, regenerate or update its consumers using the documented command and run the corresponding consistency check.

## Subsystems

### Prompt optimizer skill

`.agents/skills/prompt-optimizer/` contains the model-neutral workflow and conditional model-family guidance. It must preserve user intent, exact literals, project rules, constraints, output requirements, and approval boundaries. It may normalize a task only when the change materially improves execution.

### Model registry and routing

The registry resolves exact model IDs and explicitly supported aliases. Resolution must prefer reliable runtime information and use a neutral fallback for unknown or ambiguous models. Do not infer a materially different variant from a family-only alias. Routing changes require negative, ambiguous, and unknown-model coverage.

### Adapters

Each adapter translates the shared behavior into a host-specific contract. The adapter manifest is authoritative for supported IDs. Adapter documentation must state model-ID exposure, AUTO/PREVIEW/OFF behavior, scope semantics, configuration locations, limitations, and approval guarantees.

An adapter change is incomplete without implementation, manifest/configuration updates, capability documentation, installer behavior, and conformance tests where applicable.

### OpenCode runtime

The OpenCode plugin resolves configuration and model behavior at dispatch time, coordinates prompt analysis and policy decisions, and maintains bounded session state. Host API limitations must be reflected in the documented guarantee; advisory PREVIEW instructions must not be described as an unconditional execution barrier.

Keep policy, risk analysis, prompt construction, quality gates, session state, and UI concerns separated according to the existing modules. Prefer pure functions for contracts and decision logic so they can be tested independently.

### Installer and lifecycle

Installer operations are transactional. Managed content may be added or updated, but unrelated user content must be preserved. Writes are atomic, idempotent, symlink-safe, and rollback-capable. Project and global locations must be tested separately when their precedence or filesystem behavior differs.

Configuration parsing must tolerate malformed or legacy input according to the documented contract and must not silently discard unrelated fields. Transaction context is scoped per operation and must not rely on process-global mutable state.

### Evaluation harness

The evaluation harness measures prompt and routing behavior using deterministic cases, provider protocols, reports, and baselines. Changes to cases, scoring, provider behavior, or model guidance require review of expected outcomes and regression coverage. A baseline must not be updated merely to make a failing candidate pass; explain the behavioral reason for intentional baseline changes.

## Dependency and data rules

- Shared contracts should not import host-specific UI or filesystem code.
- Adapter modules own host precedence and host capability translation.
- Generated files are outputs, not extension points.
- Runtime code must not depend on evaluation-only helpers.
- Tests may use deterministic providers and fixtures, but real credentials and user data are never valid fixtures.
- Public behavior changes require documentation and, when appropriate, changelog updates.

## Extension checklist

### Adding a model profile

1. Update the canonical registry and matching profile/provenance.
2. Add exact, negative, ambiguous, and unknown routing cases.
3. Regenerate routing artifacts.
4. Update compatibility/user documentation and changelog for visible behavior.
5. Run registry, routing, evaluation, and full relevant verification checks.

### Adding an adapter

1. Add the supported ID to `adapters/manifest.json`.
2. Implement the host integration without changing shared semantics.
3. Document configuration, model exposure, scope, PREVIEW guarantee, and limitations.
4. Update installer behavior and capability/conformance coverage.
5. Test AUTO, PREVIEW, OFF, `scope=first`, unknown models, malformed configuration, and preservation of user-owned files.

### Changing installer or configuration

1. Preserve unrelated data and managed-block boundaries.
2. Cover project/global precedence, repeated installation, rollback, symlinks, malformed configuration, and failure recovery as relevant.
3. Verify Python and TypeScript contracts remain aligned.
4. Run the installer, lifecycle, conformance, and cross-platform checks.

## Review questions

- Is the canonical source being changed?
- Does the change preserve backward compatibility and user-owned content?
- Are host limitations documented accurately?
- Are unknown and ambiguous inputs safe and deterministic?
- Are tests asserting behavior rather than implementation details?
- Are generated artifacts and documentation synchronized?
- Could this change expose secrets, prompt content, telemetry, or an unintended approval bypass?
