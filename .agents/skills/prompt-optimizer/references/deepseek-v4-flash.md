# DeepSeek V4 Flash prompt profile

**Provenance:** official DeepSeek V4 API/thinking/harness behavior; compact Flash prompt shape is an operational heuristic based on its fast agentic role. Checked 2026-09-06.

Compatibility note checked 2026-11-13: this is the historical optimizer profile retained for exact `deepseek-v4-flash` / `deepseek-v4-flash-0731` routing. DeepSeek's own API currently redirects the retired `deepseek-v4-flash` name to V4.1 Flash / 1017; that provider-side behavior does not silently remap an explicit historical profile on every host. Use `deepseek-flash`, `deepseek-v4.1-flash` or the supported `deepseek-v4.1-flash-1017` snapshot alias for current V4.1 guidance. Unknown variants remain unsupported.

Use a compact direct brief: task, relevant context, hard constraints, execution authorization, required verification, done criteria. Minimize role-play and tool narration. Preserve autonomy for the harness/tool loop.

Do not add textual CoT triggers to compensate for native thinking. Keep `reasoning_content` and thinking effort in the harness, not the prompt.

Official sources: https://api-docs.deepseek.com/guides/thinking_mode/ ; https://www.deepseek.com/harness/en/
Current API version/retirement note: https://api-docs.deepseek.com/quick_start/pricing
Runtime: `harness-deepseek-v4.md`.
