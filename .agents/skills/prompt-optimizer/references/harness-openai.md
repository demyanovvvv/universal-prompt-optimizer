# OpenAI GPT-6.2 harness notes

## GPT-6.2 Astra and Sol
- GPT-6.2 rejects `reasoning.effort: "none"`; begin a new integration at `medium`, or `low` when migrating from `none` / `minimal`. This is an API starting point, not prompt text or a universal runtime setting.
- Responses API tool calls require the Responses API. Chat Completions is supported, but tool calling is not.
- Remove unsupported `temperature`, `top_p`, and the documented logprob controls for the selected endpoint.
- To cache reusable instructions, put them in a `developer` message at the start of `input`; top-level `instructions` are appended after `input` for GPT-6.2 and are for request-specific guidance.
- Keep the input prefix unchanged where possible; some prefix edits, model changes, or end-user/organization changes drop reasoning items and can reduce quality or repeat work.
- Check current caching TTL, cache boundaries, and billing when migrating; API cache controls are not prompt wording.

Sources:
https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#migration-quickstart
https://developers.openai.com/api/docs/guides/prompt-caching#how-prefix-matching-works

# OpenAI GPT-5.6 / GPT-6 harness notes

Runtime settings are not prompt text.

## GPT-5.6
- Responses API is the preferred surface for reasoning/tool/multi-turn workflows.
- Reasoning effort supports `none`, `low`, `medium`, `high`, `xhigh`, `max`; evaluate representative tasks instead of forcing max.
- Preserve/reuse reasoning via supported Responses mechanisms when the harness supports it.
- GPT-5.6 supports programmatic tool calling and multi-agent orchestration; use them only for workflows that benefit.
- Prompt caching can reduce repeated prefix cost; keep stable reusable prefixes and monitor cache economics.

## GPT-6 Astra
- Reasoning effort supports `low` and above; `none` is not supported.
- Tool calling requires Responses API in current guidance.
- Remove unsupported `temperature`, `top_p`, and related logprob controls documented by OpenAI.
- For mid-conversation effort changes, prefer supported configuration updates where available so prompt-prefix caching remains stable.

## GPT-6 Sol and Luna
- Reasoning effort supports `none`; preserve the effective existing effort where possible and compare representative tasks when changing it.
- For reasoning with tools, prefer the Responses API. Chat Completions function calling is limited to `reasoning_effort: "none"` in the current migration guidance.
- When reasoning effort is not `none`, remove `temperature`, `top_p`, `top_logprobs`, and corresponding logprob controls documented by OpenAI.
- For mid-conversation effort changes, use supported `configuration_update` input items where available to preserve the cached prompt prefix.
- Prompt caching uses `prompt_cache_options.ttl: "30m"` for migrations from older families; cache and billing behavior remain harness concerns.

Sources:
https://developers.openai.com/api/docs/guides/latest-model
https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
