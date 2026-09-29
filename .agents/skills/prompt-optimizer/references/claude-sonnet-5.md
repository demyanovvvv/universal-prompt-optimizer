# Claude Sonnet 5 prompt profile

**Provenance:** official Anthropic model-specific guide + shared Claude best practices, checked 2026-09-29.

Use a direct task with explicit affected scope, requirements, constraints and acceptance criteria. Sonnet 5 follows instructions literally, especially at lower effort, so spell out propagation to all affected components/states/routes/breakpoints when required.

For frontend, give concrete visual direction/tokens/reference constraints rather than generic aesthetic adjectives. Explicitly steer response length/style only when the deliverable needs it. Trigger tools/search directly when evidence matters rather than adding “think harder”.

For review, give concrete reportable failure criteria rather than an invented vague severity cutoff; preserve a threshold the user explicitly requested. Avoid fixed-cadence status messages unless progress updates need tuning.

Do not use old manual thinking-budget/CoT scaffolding; adaptive thinking/effort is runtime.

For long context, label sources and put the request after them; use examples/XML only when they clarify difficult output or boundaries. Verify requested coding behavior rather than optimizing only for passing tests.

Official source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5
Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
