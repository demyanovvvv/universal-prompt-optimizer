# Repository development rules

## Purpose

This repository provides adaptive, model-aware prompt optimization and adapters for coding agents, preserving user intent and constraints without a separate optimizer LLM call. Changes must preserve host-agent approval boundaries, adapter compatibility, and the local-only privacy contract.

## Rule precedence

Apply instructions in this order:

1. System, security, and host-agent constraints.
2. Explicit user requirements and approval boundaries.
3. The nearest applicable `AGENTS.md` file; child rules override this file only for their scope.
4. `CONTRIBUTING.md`, `TESTING.md`, `SECURITY.md`, and subsystem documentation.
5. General engineering best practices.

If two repository documents disagree, follow the more specific and newer contract, then update the documentation so the conflict does not remain.

## Required workflow

Before editing:

1. Inspect `git status --short` and preserve existing user changes.
2. Locate the relevant implementation, tests, documentation, and canonical data source.
3. Read the smallest useful ranges and identify generated artifacts before changing anything.
4. State the intended scope and choose the smallest coherent change.

While editing:

- Preserve unrelated behavior, formatting, and user-owned content.
- Prefer existing abstractions and naming conventions over new patterns.
- Keep changes focused; do not mix opportunistic refactors with behavior changes.
- Update tests and documentation in the same change when the public or contractual behavior changes.
- Never add telemetry, hidden network calls, credential collection, or persistence of raw user prompts.
- Never guess a materially different model variant or capability.

After editing:

1. Inspect the diff and confirm only intended files changed.
2. Run the checks required by the change type in `TESTING.md`.
3. Report exact commands and results. Do not claim a check passed unless it was run successfully.
4. Mention any unavailable checks or remaining uncertainty explicitly.

## Architecture invariants

- Canonical sources must be edited instead of generated artifacts. Model registry outputs are regenerated with `npm run generate:model-registry` and checked with `npm run check:model-registry`.
- Supported adapters are declared in `adapters/manifest.json`; adapter implementation, capability documentation, installer behavior, and conformance coverage must remain synchronized.
- Python installer configuration rules in `config_contract.py` and the equivalent pure TypeScript OpenCode contract must remain behaviorally aligned.
- Installer writes must be atomic, idempotent, symlink-safe, rollback-capable, and preserving of unrelated JSON fields, user-owned hooks, and text outside managed blocks.
- Unknown or ambiguous models use the configured `skip` or `generic` policy; routing must not silently upgrade an alias to a different model variant.
- Prompt shaping must remain separate from runtime reasoning, thinking, or tool-history settings.
- Runtime state is bounded and process-local; raw prompt text must not be persisted as metrics or telemetry.
- PREVIEW behavior must respect the host adapter's actual cancellation and approval capabilities; documentation must not promise a stronger guarantee than the host API provides.

## Testing and completion

Use the change matrix in `TESTING.md`. At minimum, every implementation change needs the narrowest relevant tests, and every user-visible behavior change needs documentation review. Model, adapter, installer, lifecycle, and evaluation changes have additional mandatory checks described there.

A change is complete only when the requested behavior is implemented, relevant tests pass, generated artifacts are synchronized, documentation is current, security and privacy invariants hold, and the final diff is limited to intended files.

## Git and review rules

- Do not commit, amend, push, force-push, or alter Git configuration unless explicitly requested.
- Do not delete or overwrite existing user changes.
- Do not commit secrets, credentials, runtime state, generated backups, or fixtures containing real user data.
- Keep commits and pull requests small enough to review, with a clear user-facing or technical purpose.
- Explain compatibility impact and migration requirements for breaking changes.

See `ARCHITECTURE.md` for subsystem boundaries and `CONTRIBUTING.md` for contribution procedures.
