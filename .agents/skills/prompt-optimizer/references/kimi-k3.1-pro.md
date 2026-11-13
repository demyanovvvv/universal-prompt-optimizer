# Kimi K3.1 Pro prompt profile

**Provenance:** official Moonshot Kimi K3.1 Pro API quickstart, models overview, tool-calling and prompt best-practice documentation plus the Hugging Face model card, checked 2026-11-13. The API ID is `kimi-k3.1-pro` (Hugging Face org `moonshotai`). `kimi-k3.1-pro-highspeed` is a separate unrequested variant with the same intelligence and parameter rules, not an alias; `kimi-k3` is a different model and K3.1 Pro is not part of the K2.x line.

Keep a compact objective/context/requirements/constraints/acceptance brief and preserve end-to-end autonomy and tool use for long-horizon work.

- Do not request hidden chain-of-thought, a visible reasoning plan, or anything like "think step by step": thinking is always on and cannot be disabled. `reasoning_effort` (`low`, `high`, `max`, default `max`) is a runtime choice, not prompt text; do not hard-code `max` merely because it is the default.
- Moonshot's shared prompt practices favor explicit detail and relevant context. Add delimiters, task steps or examples only when they clarify a genuinely difficult format or task; reference-based answers should cite supplied evidence and report missing information. Paragraph/bullet limits can help when the user leaves length open, but never replace exact word counts, schemas or steps the user supplied.
- Write steps for the task, not for the model's reasoning. Since preserved thinking is mandatory, keep the brief's instructions distinct from the harness's history handling.
- Tool discovery and fixed sampling values belong in the harness notes, not new prompt instructions. Do not alter the host's tools or remove exact parameters the user asked to discuss or preserve.

Preserved thinking history, cache TTL and effort selection are harness concerns (`harness-kimi-k3.md`).

Official sources:
- Quickstart: https://platform.kimi.ai/docs/guide/kimi-k3-1-pro-quickstart
- Reasoning effort: https://platform.kimi.ai/docs/guide/use-reasoning-effort
- Tool calling best practices: https://platform.kimi.ai/docs/guide/kimi-k3-tool-calling-best-practice
- Prompt best practices: https://platform.kimi.ai/docs/guide/prompt-best-practice
- Model card: https://huggingface.co/moonshotai/Kimi-K3.1-Pro

Runtime: `harness-kimi-k3.md`.
