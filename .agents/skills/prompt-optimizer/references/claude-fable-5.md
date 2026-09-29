# Claude Fable 5 prompt profile

**Provenance:** official Anthropic model-specific guide + shared Claude best practices, checked 2026-09-29.

Prefer `objective → why/context → boundaries → requirements → acceptance criteria → autonomous execution`. Fable 5 is built for complex long-horizon end-to-end work, so remove old scaffolding that prescribes dozens of microsteps unless those steps are externally required.

- Give the reason/intent behind substantial requests when it helps connect multiple workstreams.
- Make scope and mutation boundaries explicit: distinguish assessment-only tasks from authorized changes; avoid unrelated refactors, speculative abstractions and unrequested state changes.
- Let the model choose its implementation path once it has enough evidence; pause only for genuinely destructive/irreversible actions, real scope changes, or input only the user can provide.
- Ground progress claims in actual tool results on long runs; do not claim tests/actions that were not observed.
- For genuinely long-running work, add **periodic specification-based self-verification** when useful. Anthropic specifically recommends explicit long-run verification and notes that a separate fresh-context verifier can outperform self-critique. This is conditional long-run scaffolding, not a generic final `double-check everything` rule.
- Use parallel subagents for genuinely independent long-running work when the harness supports them; keep the lead agent productive instead of blocking by ritual.
- Lead user-facing completion with the outcome; keep supporting detail selective and readable.
- For long context, label sources and put the request after them; use examples/XML only when they clarify difficult output or boundaries. Verify coding behavior rather than optimizing only for passing tests.

Never ask for full/private reasoning or reasoning extraction.

Official source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
