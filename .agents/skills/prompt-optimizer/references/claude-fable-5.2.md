# Claude Fable 5.2 prompt profile

**Provenance:** official Anthropic Fable 5.2 prompting guide and what's-new/migration pages plus shared Claude best practices, checked 2026-11-13. The vendor model ID is `claude-fable-5-2`; the aggregator form `anthropic/claude-fable-5.2` resolves to that ID. Fable 5.2 is not Fable 5.1, and `claude-mythos-5-2` (identical capabilities, gated access) is not an alias.

Start from the Fable 5 end-to-end framing, then apply these 5.2-specific rules when relevant:

- Effort calibration belongs in `harness-claude.md`; do not insert a level or change host settings while shaping the prompt.
- Do not add optimizer-generated "answer directly without deliberating" lines: they no longer suppress thinking at `medium` and above. Preserve any explicit user requirement for concise output; effort is not output-length control.
- Up to the user's authorization, do not stop while requested work is outstanding. Ordinary obstacles (errors, timeouts, locked files, empty results, failing tools) should be diagnosed and worked through; deliberate blockers (protected files, withheld access, safety guardrails) should be left alone and reported.
- When adding a genuinely missing authorization boundary, make it narrow and specific. Preserve every existing host/user prohibition and confirmation boundary verbatim; do not turn a user's "never" into "ask first" or prune project rules because a vendor guide suggests reducing stale caution.
- Be explicit about code ownership only when restructuring is wanted; otherwise state a minimal-change scope. The ownership framing measurably increases consolidation but also output volume and unwanted adjacent changes.
- Do not ask the model to write out its reasoning: on 5.2 that is both unnecessary and a refusal category (`reasoning_extraction`).
- Do not add arbitrary sentence-length or word-count caps. Preserve exact style and output limits the user actually requested.
- For final reports and handoffs, ask for self-contained, low-context-readable prose with key points first, because the reader has not seen the tool calls or files.
- Ask for user-facing progress only when a human is actually watching; progress updates otherwise arrive as thinking blocks that the harness controls.
- Do not inject standing delegation or token-budget scaffolding; retain explicit task requirements and the host's actual delegation policy.
- For long context, label sources and put the request after them; use examples/XML only when they clarify difficult output or boundaries. For coding, verify behavior rather than optimizing only for passing tests.

Preserved thinking blocks, prefix binding and mid-conversation instruction mechanics are harness concerns (`harness-claude.md`), not prompt text.

Official sources:
- Model-specific guide: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2
- What's new: https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2
- Migration guide: https://platform.claude.com/docs/en/models/fable-5-2/migration-guide
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort

Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
