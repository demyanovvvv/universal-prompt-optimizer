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
- the matching manual `prompt-*` skill;
- OpenCode and Pi routing tables;
- model-specific evaluation cases and negative/ambiguous aliases;
- README, compatibility notes, and changelog when user-visible behavior
  changes.

Never infer a materially different model variant from a bare family alias.
Unknown models must follow the configured `skip` or `generic` policy.

## Adding an adapter

Document the adapter's exact model-ID exposure, PREVIEW guarantee, scope
semantics, configuration locations, and limitations. Add conformance coverage
for AUTO/PREVIEW/OFF, `scope=first`, unknown models, malformed configuration,
and preservation of user-owned hooks/files.

## Installer changes

The installer must preserve unrelated JSON fields, user-owned hooks, and text
outside managed blocks. Writes should remain atomic, symlink-safe, idempotent,
and rollback-capable. Test project and global paths where the behavior differs.
