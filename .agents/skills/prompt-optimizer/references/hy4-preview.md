# Hy4-preview prompt profile

**Provenance:** official Tencent model card/runtime guidance; overthinking/over-verification mitigation follows documented model limitations. Checked 2026-09-06.

Use a direct goal, relevant context, boundaries/constraints, done criteria and a clear stop condition. For simple direct work keep instructions minimal.

Suppress generic `think deeply/thoroughly`, exhaustive exploration, repeated `double-check` and unnecessary verification loops. Do not reopen a settled decision without new contradictory evidence. Stop once the requested acceptance criteria are satisfied.

Reasoning mode and sampling belong to runtime.

Official source: https://huggingface.co/tencent/Hy4-preview
Runtime: `harness-hy4-preview.md`.
