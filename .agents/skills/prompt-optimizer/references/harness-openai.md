# OpenAI GPT-5.6 / GPT-6 Astra harness notes

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

Sources:
https://developers.openai.com/api/docs/guides/latest-model
https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
