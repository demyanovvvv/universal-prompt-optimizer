# DeepSeek V4.1 Flash prompt profile

**Provenance:** official DeepSeek V4.1 Flash release/model/API/thinking/tool/vision/JSON documentation and the V4.1 text encoding reference, snapshot `DeepSeek-V4.1-Flash-1017`; compact Flash prompt shape is an operational heuristic based on its fast agentic role. Checked 2026-11-13.

DeepSeek V4.1 Flash is the smallest model of the V4.1 architecture family with native visual understanding. It is served as `deepseek-flash` on the official API; `-1017` is the current served snapshot of that ID, not a separately routable model. The retired `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` names still route here, while `deepseek-v4-pro` continues to be served as its own separately priced model (`DeepSeek-V4-Pro-0813`) — it does not redirect to V4.1 Flash. Treat `deepseek-v4.1-flash`, `deepseek-v4-1-flash`, `deepseek-v4.1-flash-1017` and `deepseek-flash` as this profile; keep legacy V4 Flash aliases explicit and do not infer V4.1 from a bare `deepseek-v4` family alias.

Use a compact direct brief: task, decisive context, exact literals, hard constraints, execution authorization, required verification, and observable done criteria. Let the model carry authorized reversible work through implementation and proportionate validation instead of adding step-by-step choreography. The official 1017 update reports shorter task runtime and output; explicitly retaining required depth/coverage is an optimizer heuristic, not a vendor requirement to expand every prompt.

- Native thinking is on by default at `high` effort. Never add textual CoT triggers such as `think step by step`, `think harder`, or requests to reveal reasoning; keep `reasoning_content` and effort in the harness, not the prompt. In thinking mode `temperature`, `presence_penalty` and `frequency_penalty` are accepted but ignored, and `top_p` only applies in thinking mode (clamped to 0.95–1.0), so do not steer quality through sampling text.
- Preserve user/project-required checks. Prefer a concrete verification signal and report tool output rather than asserting success.
- Ask for the output shape explicitly when correctness depends on it: schema, field names, ordering, or exact format. For JSON output the API requires the word `json` in the prompt, an example of the desired object, and a sufficient output budget.
- Where tool-schema work is requested and the host supports DeepSeek's beta strict mode, use explicit schemas (`strict: true`, `additionalProperties: false`, all properties required). Do not change the endpoint or tools during ordinary prompt shaping. Preserve tool-loop history requirements in the host; see the harness notes.
- For image/screenshot/chart input, state the concrete elements to extract or verify (text, regions, numbers, tables, discrepancies) instead of a generic "look at this".
- Keep scope bounded: report adjacent findings separately rather than repairing unrelated pre-existing issues.

Official sources:
- https://api-docs.deepseek.com/news/news260910
- https://api-docs.deepseek.com/updates/
- https://api-docs.deepseek.com/quick_start/pricing
- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/guides/tool_calls/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/guides/vision
- https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017

Runtime: `harness-deepseek-v4.md`.
