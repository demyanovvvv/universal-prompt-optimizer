import type { Profile, QualityGate, Settings } from "./types"

export const BASE_COMMON = `Preserve the user's intent, language, exact literals, hard constraints, requested output, project rules, required verification and approval boundaries. Do not invent requirements. Resolve shorthand from relevant conversation/repository context without copying irrelevant history. State instructions once and keep the final execution brief as short as the task/model permits. For implementation, do authorized in-scope local work and proportionate non-destructive validation; confirm destructive, irreversible, external, costly, credential/security-sensitive or materially scope-expanding actions unless already authorized. Native Reasoning First: never request hidden chain-of-thought or inject generic 'think step by step/think harder/show reasoning' scaffolding. User instructions outrank this preflight.`
export const BASE_GATE = `Prompt Optimizer v5.5 preflight. Apply a positive-value quality gate before acting: PASS if the user's request is already precise; LIGHT if only scope/constraint/done criteria need normalization; FULL only for genuinely complex/ambiguous work. ${BASE_COMMON}`
export const BASE_ALWAYS = `Prompt Optimizer v5.5 preflight. Quality gate is disabled: normalize every in-scope user request into the leanest model-appropriate execution brief before acting, without adding requirements or unnecessary structure. ${BASE_COMMON}`
export const PREVIEW = `PREVIEW MODE. Before any mutating or external action, build the exact optimized execution prompt for this user-turn. Read-only inspection is allowed only when necessary to resolve references. If the OpenCode question tool is available and this user-turn does not already contain an approved Prompt preview, call it exactly once with header "Prompt preview". Put the exact optimized prompt in the question text. Put option "Выполнить" first/default and option "Изменить" second; custom input is allowed. If approved, execute the previewed brief without asking again. If the user edits/customizes it, treat the edited version as source of truth. If the question tool is unavailable, print the optimized prompt and stop for explicit confirmation. Never pretend approval occurred.`

export const PROFILE_HINTS: Record<Profile, string> = {
  astra: "GPT-6 Astra: keep prompts lean and narrowly scoped. For authorized implementation/bugfix work, continue through implementation, inspection, fixes caused by the change, and affected validation until done or concretely blocked; avoid needless approval pauses, repo-wide reading, and generic over-testing.",
  sol: "GPT-5.6 Sol: lean outcome-focused brief, decisive context, autonomy/approval boundaries, success criteria, focused tools.",
  terra: "GPT-5.6 Terra: lean complete brief, one instruction once, autonomy/approval boundaries, focused tools, proportionate validation.",
  luna: "GPT-5.6 Luna: leanest bounded GPT-5.6 brief without losing correctness-critical context.",
  "glm-5.2": "GLM-5.2: direct objective/context/constraints/acceptance; avoid redundant planning and manual reasoning scaffolding.",
  "glm-5.3": "GLM-5.3: outcome/context/hard constraints/acceptance/autonomous end-to-end; avoid microstep scaffolding.",
  "glm-5.3-flash": "GLM-5.3 Flash: compact direct task/context/constraints/acceptance; use concise tool-oriented instructions.",
  "deepseek-v4-flash": "DeepSeek V4 Flash: compact direct task/context/constraints/required verification/done; no role-play/tool narration or manual CoT.",
  "deepseek-v4-pro": "DeepSeek V4 Pro: explicit objective/context/constraints/acceptance and autonomous tool feedback; avoid repetitive decomposition.",
  "claude-fable-5.1": "Claude Fable 5.1: Fable end-to-end framing plus targeted edits over whole-file rewrites, batch independent tool calls, explicit search trigger at low effort when evidence matters, scope/test guardrails; use Claude XML/examples/long-context ordering conditionally.",
  "claude-fable-5": "Claude Fable 5: objective/why/context/boundaries/acceptance with strong autonomy; ground progress in tool evidence; prevent unrelated scope; remove legacy microsteps/reasoning extraction.",
  "claude-opus-5": "Claude Opus 5: complete substantial task spec upfront and precise scope; preserve required checks but suppress added generic double-check/final-review/verifier-agent scaffolding; delegate only genuinely independent sizeable work.",
  "claude-opus-4.8": "Claude Opus 4.8: literal explicit propagation across all affected components/routes/states/variants/breakpoints; explicitly require tool evidence when needed; frontend gets concrete design tokens/reference direction, not vague aesthetics.",
  "claude-sonnet-5": "Claude Sonnet 5: direct task + explicit affected scope/constraints/acceptance; literal propagation when needed; concrete frontend direction; no legacy manual thinking-budget/CoT scaffolding.",
  "kimi-k3": "Kimi K3: compact objective/context/requirements/constraints/acceptance, end-to-end autonomy; no manufactured reasoning plan; preserved reasoning history is harness-only.",
  "muse-spark-1.3": "Muse Spark 1.3: specify why/inputs/objective/deliverable/structure/audience/quality, not tool choreography; allow genuine ambiguity questions and consequential-action confirmation; max reasoning is capability-gated.",
  "hy4-preview": "Hy4-preview: direct goal/context/boundaries/done/stop; suppress think-deeply, exhaustive exploration and repeated generic verification; do not reopen settled decisions without new evidence.",
  "qwen3.8-max": "Qwen3.8-Max: objective/context/requirements/hard constraints/acceptance with autonomous tool-feedback loops; no repeated manual decomposition/CoT; clear tool descriptions, parallelize independent calls; history/tool-choice belongs to harness.",
  "gemini-3.8-flash": "Gemini 3.8 Flash: especially concise/direct; aggressively PASS/LIGHT; for long context put data first and specific task at end; avoid verbose legacy prompt frameworks and manual CoT.",
  "grok-4.6": "Grok 4.6: direct objective/context/constraints/evidence-tool policy/acceptance; native reasoning handles depth; avoid repeated restatement in long loops.",
}

export const GENERIC = "Neutral fallback profile. Use only model/provider-neutral shaping; do not assume provider-specific reasoning, sampling, tool-history or cache behavior."

export function buildLifecycle(settings: Settings): string {
  return `Lifecycle: this instruction is bound to the current admitted user-turn. scope=${settings.scope}; behavior=${settings.behavior}; qualityGate=${settings.qualityGate}. Tool continuations remain in the same turn and must not create a second preview.`
}

export function qualityText(gate: Exclude<QualityGate, "adaptive">): string {
  return `Selected quality gate: ${gate.toUpperCase()}.`
}
