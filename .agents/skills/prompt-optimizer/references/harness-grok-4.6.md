# Grok 4.6 harness notes

- `reasoning_effort`: `low`, `medium`, `high` (default), `xhigh`; reasoning cannot be disabled.
- Do not send unsupported reasoning-model penalty/stop parameters documented by xAI.
- Set `prompt_cache_key` on Responses API or `x-grok-conv-id` on Chat Completions for reliable conversation cache routing.
- Long agent loops benefit from context compaction.

Sources:
https://docs.x.ai/developers/grok-4-6
https://docs.x.ai/developers/model-capabilities/text/reasoning
