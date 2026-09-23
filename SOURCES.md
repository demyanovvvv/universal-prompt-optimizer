# Source provenance — Universal Prompt Optimizer v5.5

Checked: **2026-09-23** for the GPT-6 family; other profiles retain their per-file checked dates.

Rule precedence inside profiles:

1. official model-specific prompt guide;
2. official family prompt guide;
3. official model/API/harness documentation;
4. explicitly marked derived operational heuristic.

A benchmark/default runtime parameter is not silently converted into a universal prompt rule.

## OpenAI
- GPT-6 family model/prompt guidance: https://developers.openai.com/api/docs/guides/latest-model
- GPT-6 prompting best practices: https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
- GPT-6 Astra skills, repository instructions, decision boundaries, and persistence: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- GPT-5.6 prompt guidance: https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
- Model tier positioning: https://developers.openai.com/api/docs/models

## Anthropic / Claude
- Shared prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Claude Fable 5.1: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
- Claude Fable 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- Claude Opus 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- Claude Opus 4.8: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8
- Claude Sonnet 5: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5

## Z.ai / GLM
- Prompt engineering: https://docs.bigmodel.cn/cn/guide/platform/prompt
- Coding prompting: https://docs.bigmodel.cn/cn/guide/coding/prompt
- GLM-5.2: https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2
- GLM-5.3: https://docs.z.ai/guides/llm/glm-5.3
- GLM-5.3-Flash: https://docs.z.ai/guides/vlm/glm-5.3-flash

## DeepSeek
- Thinking Mode: https://api-docs.deepseek.com/guides/thinking_mode/
- Tool Calls: https://api-docs.deepseek.com/guides/tool_calls/
- DeepSeek Harness: https://www.deepseek.com/harness/en/
- V4 Flash model card: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash

## Moonshot / Kimi
- Kimi K3 model card/repository: https://github.com/MoonshotAI/Kimi-K3

## Meta / Muse
- Muse Spark 1.3: https://research.meta.ai/blog/introducing-muse-spark-1-3

## Tencent / Hy4
- Hy4-preview model card: https://huggingface.co/tencent/Hy4-preview

## Qwen
- Qwen3.8-Max: https://www.qwencloud.com/models/qwen3.8-max
- Qwen3.8-Max-0902 snapshot: https://www.qwencloud.com/models/qwen3.8-max-0902
- Thinking: https://docs.qwencloud.com/developer-guides/text-generation/thinking
- OpenAI-compatible chat: https://docs.qwencloud.com/api-reference/chat/openai-chat
- Function calling: https://docs.qwencloud.com/developer-guides/tool-calling/function-calling

## Google / Gemini
- Gemini 3 prompt guidance: https://ai.google.dev/gemini-api/docs/generate-content/gemini-3
- Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/latest-model

## xAI / Grok
- Grok 4.6: https://docs.x.ai/developers/grok-4-6
- Reasoning: https://docs.x.ai/developers/model-capabilities/text/reasoning

## Agent/harness integration sources
- OpenCode v2 plugins: https://opencode.ai/v2/docs/build/plugins/
- OpenCode question tool: https://opencode.ai/docs/tools/
- Pi extensions: https://pi.dev/docs/latest/extensions
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
