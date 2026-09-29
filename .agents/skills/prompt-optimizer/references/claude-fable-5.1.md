# Claude Fable 5.1 prompt profile

**Provenance:** official Anthropic model-specific guide + shared Claude best practices, checked 2026-09-29.

Start from the Fable 5 end-to-end framing, then apply these 5.1-specific rules when relevant:

- Do not hard-code high/max effort in prose; Anthropic recommends re-evaluating all effort levels in runtime.
- If a long tool-driven workflow becomes silent, explicitly request useful user-facing progress updates at a sensible cadence; otherwise do not add narration.
- Batch independent tool calls when the harness supports it; do not serialize independent reads/searches without reason.
- Guard scope/test coverage: make only requested/necessary changes; report adjacent issues rather than automatically fixing everything.
- In unattended long runs, finish authorized reversible work instead of ending with an unexecuted next-step promise; an assessment or plan-only request still ends with that deliverable. Preserve exact constraints, decisions, unresolved items and validation when the harness compacts context.
- Prefer targeted/surgical file edits over whole-file rewrites when the same result is possible, reducing output tokens and time.
- At low effort, explicitly trigger search/retrieval/tool evidence when current/unknown information materially matters.
- At xhigh/max, leave adequate output room for long deliverables in runtime.
- For dense visual inputs, crop/zoom/inspect relevant regions if the harness supports it.
- If writing density/format matters, say so explicitly.
- For long context, label sources and put the request after them; use examples/XML only when they clarify difficult output or boundaries. For coding, verify behavior rather than optimizing only for passing tests.

Preserved thinking blocks/history are a harness concern and must be returned unchanged where required.

Official source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
