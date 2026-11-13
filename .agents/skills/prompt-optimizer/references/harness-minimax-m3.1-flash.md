# MiniMax M3.1 Flash harness notes

**Provenance:** official MiniMax model invocation, tool-use, prompt-caching and self-host documentation, checked 2026-11-13. These are API facts for host configuration, not prompt text or authorization to change host settings.

- API model name: `MiniMax-M3.1-Flash`, distinct from `MiniMax-M3`.
- Thinking is on by default and cannot be disabled; sending `thinking: {type: "disabled"}` or `effort: "none"` returns HTTP 400. Lower `effort` instead of trying to switch thinking off.
- `effort` accepts `low`, `medium`, `high`, `xhigh`, `max` and defaults to `max` when omitted. Field names differ per protocol: `output_config.effort` (Anthropic-compatible), `reasoning_effort` (OpenAI chat), `reasoning.effort` (OpenAI Responses). The Anthropic-compatible endpoint is MiniMax's recommended default for thinking/interleaved features.
- Append the model's complete assistant message to history on every tool turn, including `reasoning_content` or the full `thinking` content block; otherwise interleaved thinking breaks. Guard for turns that legitimately have no thinking block, but still append the full message.
- Prompt caching is automatic and prefix-ordered (system prompt, then tool list, then messages) with a 512-token minimum, so keep static content first.
- Model-card sampling recommendation is `temperature=1.0`, `top_p=0.95`.
- Self-hosted SGLang requires `--reasoning-parser minimax-m3` and `--tool-call-parser minimax-m3`; raw `<mm:think>` or tool-call tokens in `content` mean a parser is missing.

Official sources:
https://platform.minimax.io/docs/guides/text-generation
https://platform.minimax.io/docs/guides/text-m3-function-call
https://platform.minimax.io/docs/api-reference/text-prompt-caching
https://platform.minimax.io/docs/guides/local-deploy-m3-1-flash
