# DeepSeek V4 Flash prompt profile

**Provenance:** official DeepSeek V4 API/thinking/harness behavior; compact Flash prompt shape is an operational heuristic based on its fast agentic role. Checked 2026-09-06.

Use a compact direct brief: task, relevant context, hard constraints, execution authorization, required verification, done criteria. Minimize role-play and tool narration. Preserve autonomy for the harness/tool loop.

Do not add textual CoT triggers to compensate for native thinking. Keep `reasoning_content` and thinking effort in the harness, not the prompt.

Official sources: https://api-docs.deepseek.com/guides/thinking_mode/ ; https://www.deepseek.com/harness/en/
Runtime: `harness-deepseek-v4.md`.
