# GLM harness notes

Keep runtime thinking/sampling separate from prompt shaping.

- GLM-5.3 uses native reasoning; current Z.ai docs expose `low`, `high`, `max`, with reasoning not treated as a textual CoT instruction.
- GLM-5.3-Flash examples use native thinking/reasoning controls and can stream tool output; visual feedback loops belong in task workflow, not hidden-reasoning requests.
- GLM-5.2 examples may use high/max reasoning for demanding engineering, but do not force benchmark/runtime settings into every prompt.
- Provider-compatible layers can expose different parameter names/mappings; follow the endpoint's actual schema.

Sources:
https://docs.z.ai/guides/llm/glm-5.3
https://docs.z.ai/guides/vlm/glm-5.3-flash
https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2
