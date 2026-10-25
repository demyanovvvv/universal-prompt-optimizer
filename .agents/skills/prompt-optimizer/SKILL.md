---
name: prompt-optimizer
description: Adapt a user task to the active model only when useful. Use for automatic preflight, prompt preview, prompt-only output, or an explicit model override.
compatibility: Agent Skills compatible coding agents; native routing in OpenCode/Pi and rules or hook adapters elsewhere.
metadata:
  author: developer-guidance-based
  version: "5.14"
---

# Universal Prompt Optimizer v5.14

Preserve the user's task while applying only model guidance that materially improves execution. A short, clear request should stay short.

## Priorities

Apply, in order: system/safety requirements and host system/session instructions (including OMP); explicit user instructions and approval boundaries; repository rules and contracts; task requirements; model-specific optimization; generic defaults. Optimization never weakens a higher-priority instruction or changes the host's actual tool and approval constraints.

## Route

1. Resolve the behavior supplied by the harness: `AUTO` executes silently, `PREVIEW` requires approval, and `OFF` skips automatic preflight. Manual invocation still works when automatic behavior is off.
2. Respect scope `all` or `first` as supplied by the harness.
3. Resolve the model from the first reliable source: explicit override, resolved runtime ID, exact model named by the user, configured adapter profile, then neutral fallback if enabled. Never guess between materially different variants.
4. Read only the matching profile below. For Claude, read `references/claude-family.md` only when its conditional guidance is relevant; other family profiles are likewise conditional. Runtime settings belong in the matching `harness-*.md` note and are not prompt text.
5. Select `PASS`, `LIGHT`, or `FULL`. `qualityGate=pass` (or legacy `false`) forces the leanest model-appropriate normalization; `light` and `full` select those exact levels, and only `adaptive` (or legacy `true`) selects PASS/LIGHT/FULL from the request.

Profiles:

- GPT-6 Astra -> `references/gpt-6-astra.md`
- GPT-6 Sol / `sol` -> `references/gpt-6-sol.md`
- GPT-6.1 Sol -> `references/gpt-6.1-sol.md`
- GPT-6 Luna / `luna` -> `references/gpt-6-luna.md`
- GPT-5.6 Terra / `terra` -> `references/gpt-5.6-terra.md`
- GPT-5.6 Sol / `gpt-5.6-sol` / `gpt-5.6` -> `references/gpt-5.6-sol.md`
- GPT-5.6 Luna / `gpt-5.6-luna` -> `references/gpt-5.6-luna.md`
- GLM-5.2 -> `references/glm-5.2.md`
- GLM-5.3 -> `references/glm-5.3.md`
- GLM-5.3-Flash -> `references/glm-5.3-flash.md`
- DeepSeek V4.1 Flash / `deepseek-flash` -> `references/deepseek-v4.1-flash.md`
- DeepSeek V4 Flash -> `references/deepseek-v4-flash.md`
- DeepSeek V4 Pro -> `references/deepseek-v4-pro.md`
- Claude Fable 5.1 -> `references/claude-fable-5.1.md`
- Claude Fable 5 -> `references/claude-fable-5.md`
- Claude Opus 5.5 -> `references/claude-opus-5.5.md`
- Claude Opus 5 -> `references/claude-opus-5.md`
- Claude Opus 4.8 -> `references/claude-opus-4.8.md`
- Claude Sonnet 5 -> `references/claude-sonnet-5.md`
- Claude Sonnet 5.5 -> `references/claude-sonnet-5.5.md`
- Kimi K3 -> `references/kimi-k3.md`
- Muse Spark 1.3 -> `references/muse-spark-1.3.md`
- Hy4-preview -> `references/hy4-preview.md`
- Qwen3.8-Max -> `references/qwen3.8-max.md`
- Gemini 3.8 Flash -> `references/gemini-3.8-flash.md`
- Gemini 4 Argon / `gemini-4-argon` -> `references/gemini-4-argon.md`
- Grok 4.6 -> `references/grok-4.6.md`
- Unknown -> `references/generic-agent.md` only when neutral fallback is enabled.

Short overrides `sol` and `luna` select GPT-6. Explicit GPT-5.6 IDs select their versioned profiles; never infer a GPT-6 variant from bare `gpt-6`.

Prefer official model-specific guidance over official family guidance, API/harness documentation, and explicitly marked heuristics, in that order.

## Quality gate

- `PASS`: use an already precise request unchanged. Do not load more workflow guidance or add optimizer context merely to restate it.
- `LIGHT`: add only a missing high-value scope boundary, preserved behavior, hard constraint, output shape, approval boundary, or observable done criterion.
- `FULL`: use only for genuinely complex, ambiguous, multi-part, long-horizon, multimodal, research, migration, or consequential work. Read `references/workflow-full.md`.

Never add a section merely because a template offers it.

## Invariants

Preserve the outcome, relevant context, exact literals and selected options, explicit requirements and prohibitions, unchanged behavior, authorized actions, approval boundaries, requested output, required checks, and observable success criteria. Resolve conversational shorthand only from relevant context. Distinguish explicit requirements from inferences and never invent user-mandated requirements.

Keep prompt shaping separate from reasoning effort, sampling, cache, and tool-history settings. Never request hidden chain-of-thought or add generic `think step by step`, `show reasoning`, or repeated `think harder` scaffolding.

Preserve checks required by the user/project and checks objectively necessary for completion. Add model-specific checks only when they have positive value; use the smallest meaningful validation set.

When running in OMP/Orca, follow the repository `AGENTS.md` execution policy for this skill and every generated brief. Use real session tools (`edit` for existing files, `write` for new files); do not translate model guidance into invented OMP settings or adapter support. Preserve read-only boundaries and embedded-tab-only browser restrictions in reusable prompts. Load the installed Orca/browser or computer guide before the corresponding capability is used.

Do not turn internal planning into a user-visible plan or fixed microstep recipe. If the user asks for a plan before changes, provide it and stop. Otherwise preserve model autonomy and use structure only where it reduces execution risk.

## Complete

Unless prompt-only output or PREVIEW applies, execute in the same agent turn. Make authorized in-scope local changes and proportionate non-destructive validation. Ask only for missing information that blocks correctness or for destructive, irreversible, external, costly, credential/security-sensitive, or materially scope-expanding action that was not already authorized.

Stop when the requested success criteria are met. Avoid unrelated cleanup and speculative abstractions. If blocked, return completed useful work, the concrete blocker, and the minimum missing input or permission.

For `PREVIEW`, read `references/workflow-preview.md`. If the user asks only for an optimized prompt, return that prompt and do not execute it.
