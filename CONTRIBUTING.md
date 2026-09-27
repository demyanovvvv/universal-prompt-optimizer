# Contributing

## Before opening a pull request

Run the package checks from a Git Bash or POSIX shell:

```bash
export PYTHONDONTWRITEBYTECODE=1
./verify.sh
python -m unittest discover -s tests -v
python evals/run.py
npm run verify:ts
npm run test:runtime
```

The TypeScript command requires Node.js and TypeScript. The shell and Python
checks must still pass when TypeScript is unavailable.

## Adding a model profile

Update all of these together:

- `.agents/skills/prompt-optimizer/references/model-registry.json`;
- the matching reference profile and provenance links;
- the matching internal model reference used by automatic routing;
- generated OpenCode routing artifacts and Pi routing table;
- model-specific evaluation cases and negative/ambiguous aliases;
- README, compatibility notes, and changelog when user-visible behavior
  changes.

Run `npm run generate:model-registry` after changing the canonical registry,
then `npm run check:model-registry`. OpenCode routing artifacts are generated;
do not hand-edit `adapters/opencode/plugin/model-registry.ts` or
`profile-contract.json`.

Never infer a materially different model variant from a bare family alias.
Unknown models must follow the configured `skip` or `generic` policy.

## Adding an adapter

The supported adapter IDs are declared in `adapters/manifest.json`. Update that
manifest together with the implementation, capability matrix, compatibility
documentation, and installer behavior. Conformance checks consume this
manifest rather than parsing Python source.

Document the adapter's exact model-ID exposure, PREVIEW guarantee, scope
semantics, configuration locations, and limitations. Add conformance coverage
for AUTO/PREVIEW/OFF, `scope=first`, unknown models, malformed configuration,
and preservation of user-owned hooks/files.

## Installer changes

`config_contract.py` owns Python-side managed-config validation and legacy
quality-gate normalization. The OpenCode runtime uses the corresponding pure
`adapters/opencode/plugin/config-contract.ts` module. Host-specific source
precedence stays at the adapter layer.

The installer must preserve unrelated JSON fields, user-owned hooks, and text
outside managed blocks. Writes should remain atomic, symlink-safe, idempotent,
and rollback-capable. Test project and global paths where the behavior differs.
Install transaction context is scoped with `contextvars`, not a process-global
mutable transaction variable.
