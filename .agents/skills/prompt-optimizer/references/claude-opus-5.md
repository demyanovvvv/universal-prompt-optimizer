# Claude Opus 5 prompt profile

**Provenance:** official Anthropic model-specific guide + shared Claude best practices, checked 2026-09-06.

Give the complete substantial task specification up front: objective, relevant context, non-negotiable constraints, precise scope, acceptance criteria and deliverable. Let Opus execute end-to-end.

Explicitly bound scope; Opus can expand cleanup/refactoring beyond what was asked.

**Verification:** preserve user/project/task-required checks, but do NOT automatically add generic `double-check everything`, repeated final-review loops or verifier-subagent scaffolding. Anthropic documents that Opus 5 already self-verifies and such prompts can cause wasteful over-verification.

Use subagents only for sizeable genuinely independent work; do not use them as ritual verifiers. Control visible answer length/progress cadence in the prompt when required; effort is not an output-length control.

Official source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
Runtime: `harness-claude.md`.
