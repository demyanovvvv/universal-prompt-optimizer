# Contributing

## Development workflow

1. Read the applicable `AGENTS.md`, `ARCHITECTURE.md`, `TESTING.md`, and subsystem documentation.
2. Run `git status --short` before editing and preserve existing user changes.
3. Identify the canonical source, generated consumers, relevant tests, and documentation.
4. Make the smallest coherent change; avoid unrelated refactors.
5. Update implementation, tests, and user-facing documentation together when behavior changes.
   Keep `README.md` / `README.ru.md` and `USAGE.md` / `USAGE.ru.md` aligned;
   document host-specific behavior in the matching adapter README.
6. Inspect `git diff` and run the checks selected from the `TESTING.md` matrix.
7. Report the exact commands and results in the pull request or handoff.

## Before opening a pull request

The CI-equivalent local sequence is documented in `TESTING.md`. For a complete local check, run:

```bash
npm ci
npm run check:model-registry
npm test
npm run verify:ts
npm run test:registry
npm run test:adapters
npm run test:evals:strict
npm run test:evals:mock
npm run test:evals:baseline
npm run verify
npm run verify:bash
```

For a focused change, run at least the narrowest relevant checks from the testing matrix. Do not claim a check passed unless it was actually run. If a tool is unavailable, document the limitation and run the remaining applicable checks.

## Adding a model profile

Update all of these together:

- `.agents/skills/prompt-optimizer/references/model-registry.json`;
- the matching reference profile and provenance links;
- the matching internal model reference used by automatic routing;
- generated OpenCode routing artifacts and Pi routing table;
- model-specific evaluation cases and negative/ambiguous aliases;
- README, compatibility notes, and changelog when user-visible behavior
  changes.

Run `npm run generate:model-registry` after changing the canonical registry, then `npm run check:model-registry`. OpenCode routing artifacts are generated; do not hand-edit `adapters/opencode/plugin/model-registry.ts` or `profile-contract.json`.

Never infer a materially different model variant from a bare family alias. Unknown models must follow the configured `skip` or `generic` policy. Routing changes must cover exact IDs, supported aliases, negative aliases, ambiguous aliases, and unknown IDs.

## Adding or changing an adapter

The supported adapter IDs are declared in `adapters/manifest.json`. Update that manifest together with the implementation, capability matrix, compatibility documentation, and installer behavior. Conformance checks consume this manifest rather than parsing Python source.

Document the adapter's exact model-ID exposure, PREVIEW guarantee, scope semantics, configuration locations, and limitations. Add conformance coverage for AUTO/PREVIEW/OFF, `scope=first`, unknown models, malformed configuration, and preservation of user-owned hooks/files.

Do not describe an advisory host instruction as a guaranteed cancellation or mutation barrier when the host API cannot provide one.

## Installer and configuration changes

`config_contract.py` owns Python-side managed-config validation and legacy quality-gate normalization. The OpenCode runtime uses the corresponding pure `adapters/opencode/plugin/config-contract.ts` module. Host-specific source precedence stays at the adapter layer.

The installer must preserve unrelated JSON fields, user-owned hooks, and text outside managed blocks. Writes should remain atomic, symlink-safe, idempotent, and rollback-capable. Test project and global paths where the behavior differs.

Install transaction context is scoped with `contextvars`, not a process-global mutable transaction variable. Changes to config parsing or writes must cover malformed input, repeated installation, rollback/failure recovery, and symlink behavior as relevant.

## Evaluation and baselines

Use deterministic cases and mock providers for repeatable local checks. Update a baseline only when the intended behavior or scoring contract changed and the new result has been reviewed. Never weaken a baseline solely to hide an unexplained regression. Include the behavioral reason for baseline changes in the pull request.

## Documentation and compatibility

Update user-facing documentation when behavior, configuration, supported models, adapters, guarantees, installation, or compatibility changes. Update `CHANGELOG.md` for release-visible changes. Explain migration requirements for breaking changes and preserve legacy configuration behavior unless a documented migration intentionally changes it.

## Review expectations

Keep changes focused and reviewable. Do not commit secrets, credentials, runtime state, generated backups, or fixtures containing real user data. Do not add telemetry, hidden network calls, or persistence of raw user prompts. Use the repository pull request checklist and confirm that only intended files changed.
