# DeepSeek V4.1 Flash prompt profile

**Provenance:** official DeepSeek V4.1 Flash release/model/API/thinking/tool/vision/JSON documentation; compact Flash prompt shape is an operational heuristic based on its fast agentic role. Checked 2026-09-24.

DeepSeek V4.1 Flash is the smallest model of the V4.1 architecture family with native visual understanding. It is served as `deepseek-flash` on the official API; the retired `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` IDs still route to it, and `deepseek-v4-pro` requests are temporarily served by it at V4.1 Flash rates until V4.1-Pro launches. Treat `deepseek-v4.1-flash`, `deepseek-v4-1-flash`, and `deepseek-flash` as this profile; keep legacy V4 Flash aliases explicit and do not infer V4.1 from a bare `deepseek-v4` family alias.

Use a compact direct brief: task, decisive context, exact literals, hard constraints, execution authorization, required verification, and observable done criteria. Let the model carry authorized reversible work through implementation and proportionate validation instead of adding step-by-step choreography.

- Native thinking is on by default at `high` effort. Never add textual CoT triggers such as `think step by step`, `think harder`, or requests to reveal reasoning; keep `reasoning_content` and effort in the harness, not the prompt.
- Preserve user/project-required checks. Prefer a concrete verification signal and report tool output rather than asserting success.
- Ask for the output shape explicitly when correctness depends on it: schema, field names, ordering, or exact format. For JSON output the API requires the word `json` in the prompt, an example of the desired object, and a sufficient output budget.
- Prefer narrow tool descriptions with strict JSON schemas (`strict: true`, `additionalProperties: false`, all properties required) when tool-call fidelity matters. Keep assistant/tool history and `reasoning_content` intact through the tool loop.
- For image/screenshot/chart input, state the concrete elements to extract or verify (text, regions, numbers, tables, discrepancies) instead of a generic "look at this".
- Keep scope bounded: report adjacent findings separately rather than repairing unrelated pre-existing issues.

Official sources:
- https://api-docs.deepseek.com/news/news260910
- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/guides/tool_calls/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/guides/vision
- https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash

Runtime: `harness-deepseek-v4.md`.
