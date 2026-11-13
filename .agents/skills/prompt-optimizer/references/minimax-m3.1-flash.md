# MiniMax M3.1 Flash prompt profile

**Provenance:** official MiniMax model introduction, tool-use/interleaved-thinking guidance, model card sampling recommendation and self-host page, checked 2026-11-13. The API model name is `MiniMax-M3.1-Flash`. It keeps the M3 MoE architecture and is a distinct efficient tier, not an alias for `MiniMax-M3`.

Use a compact direct brief: outcome, decisive context, exact literals, hard constraints, requested deliverable and an explicit completion criterion. No dedicated M3.1 Flash task-prompting guide was found in the checked official sources; this lean shape is an optimizer heuristic, not a vendor-prescribed template. Do not import M2-specific or community observations as proven M3.1 Flash behavior or add a mandatory first-line format.

- Thinking is always on and cannot be disabled; never ask for hidden chain-of-thought or to turn thinking off. Depth is a runtime `effort` choice (`low`, `medium`, `high`, `xhigh`, `max`), not prompt text.
- MiniMax "thinks on demand": a turn may legitimately contain no thinking block, so do not write prompts that assume or require visible reasoning output.
- Do not inject sampling instructions; the model-card recommendation is documented in the harness notes, not an immutable prompt rule.
- For output format or envelope-sensitive deliverables, state the required format and what must be returned in full.

Preserved thinking history and effort selection are harness concerns (`harness-minimax-m3.1-flash.md`).

Official sources:
- Models intro: https://platform.minimax.io/docs/guides/models-intro
- Tool use and interleaved thinking: https://platform.minimax.io/docs/guides/text-m3-function-call
- Self-host notes (model-card sampling): https://platform.minimax.io/docs/guides/local-deploy-m3-1-flash

Runtime: `harness-minimax-m3.1-flash.md`.
