# Claude Opus 5.5 prompt profile

**Provenance:** official Anthropic Opus 5.5 model guidance, official Claude Code best practices, and Claude Opus 5.5 playbook, checked 2026-09-23.

Give the complete substantial task in one request: objective, relevant context, exact scope, constraints, observable done criteria, required checks, and when to stop and ask. Let Opus 5.5 carry authorized reversible work through completion instead of turning the next requested step into a permission question.

- Remove generic `think carefully`, `think hard`, `think step by step`, and hidden-reasoning requests. Thinking and effort belong to the runtime.
- Preserve user/project-required checks. Prefer a concrete verification signal and report command output or other evidence instead of asserting success.
- For long runs, use a compact checklist or task file only when it materially helps; preserve decisions, constraints, completed work, open items, and exact references across compaction.
- For review or research, request findings with location, impact, evidence, and what could not be confirmed. Use targeted review rather than an automatic review loop after every task.
- Delegate only genuinely independent, sizeable work when the harness supports it; do not use subagents as ritual verifiers.
- For design, preserve concrete positive direction and explicit unwanted patterns when the user provides them. For multimodal work, use the supplied image/chart/document directly and ask a concrete question.
- Keep scope bounded: do not repair unrelated pre-existing issues or turn a focused request into a broad refactor; report adjacent findings separately.

Official sources:
- https://platform.claude.com/docs/en/models/opus-5-5/overview
- https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5
- https://claude.dev/blog/getting-the-most-out-of-opus-5-5/
- https://code.claude.com/docs/en/best-practices

Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
