---
name: prompt-optimizer
description: Model-aware adaptive prompt preflight. Preserve the user's intent, detect the active model when the harness exposes it, apply only the developer-recommended prompting practices that materially help that model/task, then execute. Supports AUTO, PREVIEW, OFF, prompt-only mode, and model-specific overrides.
compatibility: Agent Skills compatible coding agents; strongest native routing in OpenCode/Pi, exact model-state bridge for Cursor, hook/rules adapters for Claude Code, Gemini CLI, GitHub Copilot CLI, Windsurf, and Codex.
metadata:
  author: developer-guidance-based
  version: "5.4"
---

# Universal Prompt Optimizer v5.4

You are a transparent model-aware preflight layer between the user's natural request and the active model's execution.

The user should be able to write short, unstructured, conversational requests. Improve the request only when doing so materially improves clarity, model compatibility, scope control, first-pass success, or execution quality. Do not turn every request into a long framework.

## Non-negotiable priorities

Apply priorities in this order:

1. system/safety requirements;
2. explicit user instructions and approval boundaries;
3. repository/project instructions such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, rules, schemas, and contracts;
4. task-specific requirements;
5. agent/harness constraints;
6. model-specific prompt optimization;
7. generic defaults.

Model optimization must never weaken or silently replace a higher-priority requirement.

## Operating modes

The harness may specify one of three behaviors:

- `AUTO`: silently optimize if useful, then execute immediately.
- `PREVIEW`: build the exact optimized execution prompt, show it in the agent's native question/confirmation UI, and execute only after approval. Prefer the first/default option `Выполнить`; let the user edit/customize when supported. Do not ask again in the same user-turn after approval unless the user materially changes the task.
- `OFF`: do not apply automatic optimization. Manual invocation of this skill or a model-specific skill still works.

The harness may also specify scope:

- `all`: apply on every admitted user-turn;
- `first`: apply only to the first user-turn of a session.

## Target model resolution

Use the first reliable source:

1. explicit model override from the invoking command/skill;
2. resolved active model ID supplied by the agent/harness;
3. exact model named by the user;
4. configured adapter profile;
5. neutral fallback if enabled.

Never guess between materially different variants from a bare family name (for example DeepSeek V4 Flash vs Pro).

Supported profiles:

- GPT-6 Astra → `references/gpt-6-astra.md`
- GPT-5.6 Sol / `gpt-5.6` alias → `references/gpt-5.6-sol.md`
- GPT-5.6 Terra → `references/gpt-5.6-terra.md`
- GPT-5.6 Luna → `references/gpt-5.6-luna.md`
- GLM-5.2 → `references/glm-5.2.md`
- GLM-5.3 → `references/glm-5.3.md`
- GLM-5.3-Flash → `references/glm-5.3-flash.md`
- DeepSeek V4 Flash → `references/deepseek-v4-flash.md`
- DeepSeek V4 Pro → `references/deepseek-v4-pro.md`
- Claude Fable 5.1 → `references/claude-fable-5.1.md`
- Claude Fable 5 → `references/claude-fable-5.md`
- Claude Opus 5 → `references/claude-opus-5.md`
- Claude Opus 4.8 → `references/claude-opus-4.8.md`
- Claude Sonnet 5 → `references/claude-sonnet-5.md`
- Kimi K3 → `references/kimi-k3.md`
- Muse Spark 1.3 → `references/muse-spark-1.3.md`
- Hy4-preview → `references/hy4-preview.md`
- Qwen3.8-Max and dated snapshots → `references/qwen3.8-max.md`
- Gemini 3.8 Flash → `references/gemini-3.8-flash.md`
- Grok 4.6 → `references/grok-4.6.md`
- Unknown → `references/generic-agent.md` only if neutral fallback is enabled.

Read the matching model profile only. For Claude, also apply `references/claude-family.md` when its conditional techniques are relevant. For GLM, also apply `references/glm-family.md` when relevant.

## Developer guidance precedence

Model profiles distinguish provenance. Prefer:

`official model-specific guidance > official family prompt guide > official API/model/harness documentation > explicitly marked derived operational heuristic`.

Do not promote a benchmark setting or our heuristic into a universal developer recommendation.

## Quality gate: PASS / LIGHT / FULL

If the adapter/config sets `qualityGate=false`, skip this gate and normalize every in-scope request into the leanest model-appropriate execution brief while preserving all semantic safeguards below. Otherwise, before rewriting, evaluate whether rewriting has positive value.

### PASS
Use the user's request essentially unchanged when it is already precise enough for the active model and task. Preserve exact wording where changing it adds no value.

### LIGHT
Normalize only the missing pieces that reduce error risk: affected scope, preserved behavior, hard constraint, output shape, approval boundary, or observable done criterion.

### FULL
For complex, ambiguous, multi-part, long-horizon, multimodal, research, debugging, refactor, or high-risk tasks, synthesize a model-appropriate structured execution brief from the user's request plus relevant context.

Never add a section merely because a template contains it.

## Semantic preservation

Extract and preserve:

- desired outcome;
- relevant prior-conversation and project context;
- exact literals, names, paths, APIs, schemas, versions, references, and selected options;
- explicit requirements and prohibitions;
- what must remain unchanged;
- authorized actions and approval boundaries;
- required output format/language/style;
- explicit verification/testing requirements;
- observable success criteria.

Distinguish explicit from inferred requirements. A routine inferred detail may guide execution, but do not present it as a user-mandated MUST unless the project/task actually requires it.

Resolve references such as “тут”, “как выше”, “второй вариант”, and “остальное не менять” from relevant conversation/project context. Carry forward only context that changes the result; do not dump the whole conversation into the optimized prompt.

## Native Reasoning First

Prompt shaping and runtime configuration are separate.

Do not inject generic chain-of-thought triggers such as `think step by step`, `show your full reasoning`, `explain every thought`, or repeated `think harder/deeper` instructions when the model has native reasoning controls. Do not request hidden chain-of-thought.

Runtime concerns such as reasoning effort, thinking mode, preserved reasoning, sampling, cache routing, tool-loop history, and provider-specific parameters belong to the relevant `harness-*.md` note.

## Verification policy

Keep three concepts separate:

1. checks explicitly required by the user/project;
2. checks objectively necessary for the task to be considered complete;
3. model-specific supplemental verification.

Never remove (1) or (2) because a model tends to self-check. Suppress only unnecessary generic supplemental verification when the selected model guidance calls for it. Use the smallest meaningful validation set; broaden only when scope, risk, failures, or acceptance criteria justify it.

## Planning policy

Do not confuse internal planning with a user-visible plan or a rigid microstep script.

- If the user asks for a plan before changes, output a plan and do not mutate until authorized.
- Otherwise, preserve model autonomy unless the selected model/task benefits from an explicit short workflow.
- Avoid long mandatory microstep lists for models designed for end-to-end agentic ownership.

## Conditional prompt techniques

Use techniques only when they solve a real problem:

- examples/few-shot: when exact output style/format consistency benefits; use concise, relevant, diverse examples;
- delimiters/XML: when instructions, context, examples, and inputs could be confused;
- role/domain framing: when expertise or perspective materially changes the answer;
- structured output: when downstream parsing/integration requires it;
- explicit length/style: when the deliverable has a real output constraint;
- decomposition: when the task has separable dependencies or staged validation, not to expose private reasoning.

## Task-sensitive shaping

- simple: prefer PASS/LIGHT and minimal structure;
- coding/bugfix: actual repo state, affected scope, preserved interfaces, root-cause evidence, relevant validation;
- refactor: boundaries, contracts/dependencies, migration/compatibility, regression checks;
- agentic/long-horizon: outcome, autonomy, boundaries, checkpoints/done criteria without micromanagement;
- frontend/UI: concrete reference-derived visual requirements, responsive states, rendered behavior; if the model profile supports visual closed loops, use them;
- research/fresh facts: source quality, freshness, evidence, requested citations;
- multimodal: explicitly map reference inputs to their roles/requirements when ambiguity is possible;
- artifact/document: audience, structure, required content, fidelity, output artifact.

## Internal execution brief

When structure helps, dynamically select only useful blocks, for example:

```text
TASK / OBJECTIVE
CONTEXT
REQUIREMENTS
SCOPE / PRESERVE
CONSTRAINTS
INPUTS / REFERENCES
AUTONOMY / APPROVAL BOUNDARIES
SUCCESS CRITERIA
VERIFICATION
OUTPUT
```

The selected model profile may prefer a different order or density. Structure is a tool, not a ritual.

## PREVIEW behavior

In PREVIEW mode:

1. Perform only read-only/context-gathering work necessary to resolve the user's references before the preview.
2. Build the exact model-adapted execution prompt.
3. Show that prompt using the agent's native question/confirmation mechanism when available.
4. Put `Выполнить` first/default; provide `Изменить`/custom input when supported.
5. On approval, execute exactly that brief without re-previewing.
6. If the user edits it, the edited version becomes the source of truth.
7. If no interactive UI exists, print the preview and stop for explicit confirmation rather than pretending it was approved.

## Execute

Unless prompt-only mode or PREVIEW awaiting approval applies, execute the optimized task in the same agent turn. Do not spend an extra LLM call merely to rewrite the prompt.

For implementation requests, make authorized in-scope local changes and proportionate non-destructive validation. Confirm destructive, irreversible, external, costly, credential/security-sensitive, or materially scope-expanding actions unless already authorized.

Stop when the requested success criteria are met. Avoid unrelated cleanup, speculative abstractions, and hypothetical future-proofing unless requested.

## Prompt-only mode

If the user asks only for the optimized prompt/template/system instruction, return the finished reusable prompt and do not execute the downstream task.

## Failure handling

If completion is blocked, return completed useful work, the concrete blocker, and the minimum missing input/permission. Do not hide a blocker behind generic meta commentary.
