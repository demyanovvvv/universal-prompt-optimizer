# Source provenance — Universal Prompt Optimizer v5.19

Checked: **2026-11-18** for GPT-6.2 Astra and Sol. Earlier dated checks below cover the models listed there. Sources were inspected without model calls; recommendations are not a measured quality or performance claim.

Rule precedence inside profiles:

1. official model-specific prompt guide;
2. official family prompt guide;
3. official model/API/harness documentation;
4. explicitly marked derived operational heuristic.

A benchmark/default runtime parameter is not silently converted into a universal prompt rule.

## November 2026 findings

| Model | Evidence and prompt-shaping decision | Separate host/API concern |
|---|---|---|
| Gemini 4 Hydrogen / Carbon / Neon / Argon | Model-specific developer guides plus shared Google prompting practices: clear outcome, relevant context, constraints and output; examples only when useful. Neon has its own model guide; no new mandatory prompt template or inherited Flash-specific quality gate. | Unified context/output headroom; 4,096-token implicit cache prefix. Hydrogen additionally documents cross-turn thought signatures and prefix-binding/compaction constraints. |
| Claude Fable 5.2 | Dedicated prompt guide: preserve whole-task completion within authorization, precise scope and useful final evidence; omit broad code-ownership wording for minimal edits and do not add “think less” scaffolding. | Adaptive thinking, effort, append-only signed history and progress-display support are host controls. |
| GLM-5.3-FlashX | Shared Flash/FlashX model page and Z.ai coding practices: goal/context/constraints/done; for visual deliverables compare actual rendered output. FlashX remains distinct from Flash. | Forced thinking, preserved reasoning history, tool streaming and sampling are API settings. |
| Kimi K3.1 Pro | Model quickstart/tool guidance plus generic Kimi prompt practices: decisive context, explicit requirements and output; distinguish task steps from instructions to expose reasoning. No dedicated K3.1 Pro prompt template found. | Full assistant-message replay, always-on thinking, effort/cache interaction and tool-call pairing. |
| MiniMax M3.1 Flash | Official model/tool-use guidance supports native adaptive thinking and full tool-message history. A lean task/context/constraints/deliverable brief is an optimizer heuristic, not a published model-specific prompt template; M2/community templates are not imported as facts. | Preserve complete assistant messages, including optional thinking blocks; effort and protocol-specific fields stay host-controlled. |
| DeepSeek V4.1 Flash / 1017 | Official changelog/card/API refresh; one profile for the requested snapshot. The 1017 release reduces runtime/output length; stating necessary depth and coverage is a derived heuristic. JSON-mode literal/example and concrete image questions remain conditional. | All-turn reasoning replay with tools, exact sampling semantics, stateless Responses API and JSON blank-content handling. |
| Muse Wonder | Official model/card/API documents, but no Wonder-specific prompt guide found. Goal, context, constraints, deliverable and completion boundaries are explicitly derived heuristics; Muse Spark Open templates and Wonder Full capabilities are not borrowed. | Vendor ID `muse-wonder-1.0`; Responses reasoning continuity differs from external-key Chat Completions. |

The registry supports provider-qualified model leaves and documented spelling aliases. A profile match is neither a provider-access guarantee nor permission to modify host settings, upload context, enable paid tools, persist prompts or weaken approval boundaries.

## OpenAI
- GPT-6.2 Astra/Sol prompting best practices: https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#prompting-best-practices
- GPT-6.2 Astra model: https://developers.openai.com/api/docs/models/gpt-6.2-astra
- GPT-6.2 Sol model: https://developers.openai.com/api/docs/models/gpt-6.2-sol
- GPT-6.2 Responses API migration: https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#migration-quickstart
- GPT-6.2 prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching#how-prefix-matching-works
- GPT-6 family model/prompt guidance: https://developers.openai.com/api/docs/guides/latest-model
- GPT-6.1 Sol model: https://developers.openai.com/api/docs/models/gpt-6.1-sol
- GPT-6 prompting best practices: https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
- GPT-6 Astra skills, repository instructions, decision boundaries, and persistence: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- GPT-5.6 prompt guidance: https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
- Model tier positioning: https://developers.openai.com/api/docs/models

## Anthropic / Claude
- Shared prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Claude Fable 5.1: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
- Claude Fable 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- Claude Fable 5.2 prompting: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2
- Fable 5.2 changes and migration: https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2 and https://platform.claude.com/docs/en/models/fable-5-2/migration-guide
- Claude Opus 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- Claude Opus 5.5 model overview: https://platform.claude.com/docs/en/models/opus-5-5/overview
- Claude Opus 5.5 changes: https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5
- Claude Opus 5.5 playbook: https://claude.dev/blog/getting-the-most-out-of-opus-5-5/
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Claude Opus 4.8: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8
- Claude Sonnet 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5
- Claude Sonnet 5.5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5

## Z.ai / GLM
- Prompt engineering: https://docs.bigmodel.cn/cn/guide/platform/prompt
- Coding prompting: https://docs.bigmodel.cn/cn/guide/coding/prompt
- GLM-5.2: https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2
- GLM-5.3: https://docs.z.ai/guides/llm/glm-5.3
- GLM-5.3-Flash/FlashX shared model page (distinct model codes): https://docs.z.ai/guides/vlm/glm-5.3-flash
- Coding-agent practices: https://docs.z.ai/devpack/resources/best-practice
- Preserved thinking and tool calling: https://docs.z.ai/guides/capabilities/thinking-mode and https://docs.z.ai/guides/capabilities/function-calling

## DeepSeek
- V4.1 Flash release: https://api-docs.deepseek.com/news/news260910
- 1017 update and current served version: https://api-docs.deepseek.com/updates/ and https://api-docs.deepseek.com/quick_start/pricing
- 1017 model card: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017
- Stateless Responses API: https://api-docs.deepseek.com/guides/responses_api
- Thinking Mode: https://api-docs.deepseek.com/guides/thinking_mode/
- Tool Calls: https://api-docs.deepseek.com/guides/tool_calls/
- JSON Output: https://api-docs.deepseek.com/guides/json_mode/
- Vision: https://api-docs.deepseek.com/guides/vision
- DeepSeek Harness: https://www.deepseek.com/harness/en/
- V4.1 Flash model card: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
- V4 Flash model card: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash

## Moonshot / Kimi
- Kimi K3 model card/repository: https://github.com/MoonshotAI/Kimi-K3
- Kimi K3.1 Pro quickstart: https://platform.kimi.ai/docs/guide/kimi-k3-1-pro-quickstart
- Kimi prompting and tool practices: https://platform.kimi.ai/docs/guide/prompt-best-practice and https://platform.kimi.ai/docs/guide/kimi-k3-tool-calling-best-practice
- K3 effort/history: https://platform.kimi.ai/docs/guide/use-reasoning-effort and https://platform.kimi.ai/docs/guide/use-thinking-models
- K3.1 Pro model card: https://huggingface.co/moonshotai/Kimi-K3.1-Pro

## Meta / Muse
- Muse Spark 1.3: https://research.meta.ai/blog/introducing-muse-spark-1-3
- Muse Wonder model and model card: https://dev.meta.ai/docs/muse-wonder and https://research.meta.ai/static/muse-wonder-model-card/
- Wonder developer introduction: https://dev.meta.ai/resources/blog/build-with-muse-wonder
- Shared hosted-API reasoning, tools and output: https://dev.meta.ai/docs/reasoning.md, https://dev.meta.ai/docs/tool-calling.md and https://dev.meta.ai/docs/structured-output.md

## MiniMax
- M3.1 Flash release: https://www.minimax.io/blog/minimax-m31f
- Model invocation: https://platform.minimax.io/docs/guides/text-generation
- Tool use and interleaved thinking: https://platform.minimax.io/docs/guides/text-m3-function-call
- API contracts: https://platform.minimax.io/docs/api-reference/text-chat-anthropic and https://platform.minimax.io/docs/api-reference/text-chat-openai

## Tencent / Hy4
- Hy4-preview model card: https://huggingface.co/tencent/Hy4-preview

## Qwen
- Qwen3.8-Max: https://www.qwencloud.com/models/qwen3.8-max
- Qwen3.8-Max-0902 snapshot: https://www.qwencloud.com/models/qwen3.8-max-0902
- Thinking: https://docs.qwencloud.com/developer-guides/text-generation/thinking
- OpenAI-compatible chat: https://docs.qwencloud.com/api-reference/chat/openai-chat
- Function calling: https://docs.qwencloud.com/developer-guides/tool-calling/function-calling

## Google / Gemini
- Gemini 4 Hydrogen/Carbon/Argon and Neon checked **2026-11-20**. Model/API facts and shared prompting practices are distinguished.
- Hydrogen developer guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-hydrogen
- Carbon developer guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-carbon
- Neon developer guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-neon
- Argon developer guide: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-4-argon
- Gemini 4 family overview: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/get-started-with-gemini-4
- Shared prompting practices: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/prompts/prompt-design-strategies
- Gemini 3 prompt guidance: https://ai.google.dev/gemini-api/docs/generate-content/gemini-3
- Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/latest-model

## xAI / Grok
- Grok 4.6: https://docs.x.ai/developers/grok-4-6
- Reasoning: https://docs.x.ai/developers/model-capabilities/text/reasoning

## Agent/harness integration sources
- OpenCode v2 plugins: https://opencode.ai/v2/docs/build/plugins/
- OpenCode question tool: https://opencode.ai/docs/tools/
- Pi extensions: https://pi.dev/docs/latest/extensions
- DeepSeek Harness native adapter contract checked **2026-11-13**, upstream `0.2.2-rc.3` APIs: [system-prompt section registration](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/system-prompt/README.md), [assembly context](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/system-prompt.md), [model selection and durable turn boundary](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/core.md), [working directory](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/working-directory.md), [CLI overlays and host telemetry](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.md), [native skill discovery](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md). This is host integration support, separate from the DeepSeek model profiles and API harness notes.
- Cursor hooks: https://cursor.com/docs/hooks
- Gemini CLI hooks: https://geminicli.com/docs/hooks/
- Gemini CLI hook reference: https://geminicli.com/docs/hooks/reference/
- Gemini CLI configuration/model precedence: https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md
- Gemini CLI ask_user: https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/ask-user.md
- GitHub Copilot CLI customization: https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli
- GitHub Copilot hooks: https://docs.github.com/en/copilot/reference/hooks-reference
- GitHub Copilot skills: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- OpenAI Codex AGENTS.md implementation/spec: https://github.com/openai/codex/blob/main/docs/agents_md.md
- OpenAI Codex AGENTS.md discovery implementation: https://github.com/openai/codex/blob/main/codex-rs/core/src/agents_md.rs
- Windsurf Rules / Memories: https://docs.windsurf.com/windsurf/cascade/memories
- Windsurf AGENTS.md: https://docs.windsurf.com/windsurf/cascade/agents-md
