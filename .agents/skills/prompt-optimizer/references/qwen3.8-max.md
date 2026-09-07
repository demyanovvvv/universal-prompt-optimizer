# Qwen3.8-Max prompt profile

**Provenance:** official QwenCloud model/thinking/tool docs, checked 2026-09-06.

State final objective, relevant context, requirements, hard constraints and acceptance criteria. Preserve autonomy to inspect the environment, use tool feedback and iterate through a closed execution loop. Avoid repeated manual decomposition/CoT scaffolding.

For multimodal work, make reference roles explicit and let the model use planning/execution/verification cycles. For tool calling, give clear specific tool/function descriptions and parallelize only independent calls.

`qwen3.8-max`, `qwen3.8-max-0902`, and aliases/snapshots use the same base profile unless a future snapshot guide explicitly differs. Thinking/history/tool-choice settings belong to runtime.

Official sources: https://www.qwencloud.com/models/qwen3.8-max ; https://docs.qwencloud.com/developer-guides/text-generation/thinking ; https://docs.qwencloud.com/developer-guides/tool-calling/function-calling
Runtime: `harness-qwen3.8-max.md`.
