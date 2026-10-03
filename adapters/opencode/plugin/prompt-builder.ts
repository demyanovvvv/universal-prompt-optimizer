import type { Profile, QualityGate, Settings, TaskType, Behavior } from "./types"
import { classifyTask } from "./task-classifier"

export const BASE_COMMON = `Preserve the user's intent, language, exact literals, hard constraints, requested output, project rules, required verification and approval boundaries. Do not invent requirements. Resolve shorthand from relevant conversation/repository context without copying irrelevant history. State instructions once and keep the final execution brief as short as the task/model permits. For implementation, do authorized in-scope local work and proportionate non-destructive validation; confirm destructive, irreversible, external, costly, credential/security-sensitive or materially scope-expanding actions unless already authorized. Native Reasoning First: never request hidden chain-of-thought or inject generic 'think step by step/think harder/show reasoning' scaffolding. User instructions outrank this preflight.`
export const BASE_GATE = `Prompt Optimizer v5.11 preflight. Apply a positive-value quality gate before acting: PASS if the user's request is already precise; LIGHT if only scope/constraint/done criteria need normalization; FULL only for genuinely complex/ambiguous work. ${BASE_COMMON}`
export const BASE_ALWAYS = `Prompt Optimizer v5.11 preflight. Quality gate is disabled: normalize every in-scope user request into the leanest model-appropriate execution brief before acting, without adding requirements or unnecessary structure. ${BASE_COMMON}`
export const PREVIEW = `PREVIEW MODE. Before any mutating or external action, build the exact optimized execution prompt for this user-turn. Read-only inspection is allowed only when necessary to resolve references. Do not call mutation-capable tools before approval. If the OpenCode question tool is available and this user-turn does not already contain an approved Prompt preview, call it exactly once with header "Prompt preview". Put the exact optimized prompt in the question text. Put option "Выполнить" first/default and option "Изменить" second; custom input is allowed. If approved, execute the previewed brief without asking again. If the user edits/customizes it, treat the edited version as source of truth. If the question tool is unavailable, print the optimized prompt and stop for explicit confirmation. Never pretend approval occurred.`

export const PROFILE_HINTS: Record<Profile, string> = {
  astra: "GPT-6 Astra: keep prompts lean and narrowly scoped. For authorized implementation/bugfix work, continue through implementation, inspection, fixes caused by the change, and affected validation until done or concretely blocked; avoid needless approval pauses, repo-wide reading, and generic over-testing.",
  sol: "GPT-6 Sol: preserve decisive context, hard constraints, approval boundaries, and observable completion; infer routine intent and follow through on authorized work with proportionate validation. For repository analysis, use bounded inspection: prioritize the current repository/configuration evidence needed by the acceptance criteria, do not infer runtime registration from stale documentation, stop tool calls once sufficient evidence is collected, and emit the requested report or an explicit blocking reason instead of continuing an open-ended exploration loop.",
  "gpt-6.1-sol": "GPT-6.1 Sol: preserve outcome, decisive context, scope, approval boundaries and observable completion. Follow through on authorized work with relevant validation; for analysis collect bounded current evidence and stop when sufficient. Keep reasoning effort in runtime, not generic think-hard prompt text.",
  terra: "GPT-5.6 Terra: lean complete brief, one instruction once, autonomy/approval boundaries, focused tools, proportionate validation.",
  luna: "GPT-6 Luna: compact bounded brief with one outcome, decisive context, hard constraints, exact output shape when needed, and correctness-critical validation.",
  "gpt-5.6-sol": "GPT-5.6 Sol: lean outcome-focused brief, decisive context, autonomy/approval boundaries, success criteria, focused tools.",
  "gpt-5.6-luna": "GPT-5.6 Luna: leanest bounded GPT-5.6 brief without losing correctness-critical context.",
  "glm-5.2": "GLM-5.2: direct objective/context/constraints/acceptance; avoid redundant planning and manual reasoning scaffolding.",
  "glm-5.3": "GLM-5.3: outcome/context/hard constraints/acceptance/autonomous end-to-end; avoid microstep scaffolding.",
  "glm-5.3-flash": "GLM-5.3 Flash: compact direct task/context/constraints/acceptance; use concise tool-oriented instructions.",
  "deepseek-v4.1-flash": "DeepSeek V4.1 Flash: compact task/context/exact literals/hard constraints/required verification/done; authorized end-to-end work; explicit output/tool-schema/JSON/image asks only when needed; no manual CoT.",
  "deepseek-v4-flash": "DeepSeek V4 Flash: compact direct task/context/constraints/required verification/done; no role-play/tool narration or manual CoT.",
  "deepseek-v4-pro": "DeepSeek V4 Pro: explicit objective/context/constraints/acceptance and autonomous tool feedback; avoid repetitive decomposition.",
  "claude-fable-5.1": "Claude Fable 5.1: end-to-end authorized work with targeted edits, batched independent tools, bounded scope and test coverage; preserve decisions across compaction; use progress, XML/examples and long-context ordering only when useful; verify behavior rather than optimizing only for tests.",
  "claude-fable-5": "Claude Fable 5: objective/context/boundaries/acceptance with strong autonomy; ground progress in tool evidence, label long-context sources, use examples/XML only when useful, prevent unrelated scope and verify behavior rather than only passing tests.",
  "claude-opus-5.5": "Claude Opus 5.5: complete task and observable done criteria; continue authorized reversible work; preserve checks; use targeted evidence, bounded scope and concrete review criteria; label long-context sources, verify behavior, and report unconfirmed work; avoid generic think-hard scaffolding.",
  "claude-opus-5": "Claude Opus 5: complete substantial task spec and precise scope upfront; preserve required checks without generic review loops; use labeled long-context sources, examples/XML only when useful, and verify behavior instead of optimizing only for tests.",
  "claude-opus-4.8": "Claude Opus 4.8: literal explicit propagation across affected components/routes/states/variants/breakpoints; require evidence when needed; use concrete review criteria and design direction; label long-context sources and verify behavior rather than only passing tests.",
  "claude-sonnet-5": "Claude Sonnet 5: direct task + explicit affected scope/constraints/acceptance; inspect relevant patterns; use concrete completion evidence and review criteria; examples/XML only when they clarify difficult structure; no legacy manual thinking-budget/CoT scaffolding.",
  "claude-sonnet-5.5": "Claude Sonnet 5.5: direct bounded task with explicit scope, initiative boundary, deliverable and verification; continue authorized work without premature check-ins, batch independent tools, use examples/XML only when useful, and report completed versus verified versus unconfirmed work; runtime controls effort.",
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

export type PromptAnalysis = {
  primaryTask: TaskType
  hasScope: boolean
  hasConstraints: boolean
  hasValidation: boolean
  hasDeliverable: boolean
  exactLiterals: string[]
  readOnly: boolean
  consequential: boolean
}

export type PromptPlanInput = {
  prompt: string
  profile: Profile | "generic"
  behavior: Behavior
  qualityGate: QualityGate
  gate: Exclude<QualityGate, "adaptive">
  taskType: TaskType
  settings?: Settings
}

export type PromptPlan = PromptPlanInput & {
  analysis: PromptAnalysis
  sections: Array<{ id: string; text: string }>
}

const pathPattern = /(?:[A-Za-z]:[\\/]|\.\.?[\\/]|(?:src|test|tests|app|lib|packages|docs)[\\/])[A-Za-z0-9_.@\\/-]+/g
const literalPattern = /`[^`]+`|"[^"\n]+"|'[^'\n]+'/g

export function analyzePrompt(prompt: string): PromptAnalysis {
  const normalized = prompt.trim()
  const exactLiterals = [...new Set([
    ...(normalized.match(pathPattern) ?? []),
    ...(normalized.match(literalPattern) ?? []).map(value => value.slice(1, -1)),
  ])]
  const readOnly = /\b(?:plan only|read[- ]only|do not (?:change|modify|edit|delete)|without changing|no changes)\b|только план|только чт|ничего не менять|без изменений/i.test(normalized)
  const consequential = /\b(?:delete|remove|drop|destroy|deploy|publish|production|prod|credentials?|secrets?)\b|удал\w*|продакшн|боев\w*|секрет\w*/i.test(normalized) && !readOnly
  const hasScope = exactLiterals.length > 0 || /\b(?:in|from|under|within|across|file|files|module|repo|repository)\b|папк|файл|проект/i.test(normalized)
  const hasConstraints = /\b(?:only|must|keep|preserve|without|don't|do not|avoid|exactly)\b|только|сохрани|сохран|без|не измен|не добав/i.test(normalized)
  const hasValidation = /\b(?:test|tests|testing|verify|validate|check|coverage|assert)\b|проверь|тест|провер/i.test(normalized)
  const hasDeliverable = /\b(?:report|document|explain|output|return|provide|show)\b|отч[её]т|документ|объясни|покажи|предложи/i.test(normalized)
  return { primaryTask: classifyTask(normalized).type, hasScope, hasConstraints, hasValidation, hasDeliverable, exactLiterals, readOnly, consequential }
}

function taskPolicy(taskType: TaskType, analysis: PromptAnalysis): string[] {
  if (taskType === "review" || taskType === "security") return ["Report findings first with location, evidence, impact, and confidence.", analysis.readOnly ? "Do not modify files or perform remediation." : "Do not modify files unless remediation is explicitly requested."]
  if (taskType === "bugfix") return analysis.readOnly
    ? ["Use read-only inspection and explain the observed cause or proposed fix without changing files."]
    : ["Identify the observable failure and root cause before changing code.", "Keep the fix in scope and address regressions caused by the change."]
  if (taskType === "refactor") return ["Preserve public behavior and contracts; update affected references and verify the result."]
  if (taskType === "migration") return ["Account for compatibility, data or schema impact, recovery considerations, and proportionate validation."]
  if (taskType === "research" || taskType === "planning") return ["Use bounded investigation, distinguish evidence from assumptions, and stop when the requested deliverable is supported."]
  if (taskType === "documentation") return ["Preserve the requested audience, source of truth, exact commands and examples, and avoid unrelated rewrites."]
  return []
}

export function buildPromptPlan(input: PromptPlanInput): PromptPlan {
  const analysis = analyzePrompt(input.prompt)
  analysis.primaryTask = input.taskType
  if (input.behavior === "off" || (input.behavior === "auto" && input.gate === "pass" && input.qualityGate === "adaptive")) return { ...input, analysis, sections: [] }
  const sections: Array<{ id: string; text: string }> = []
  const gateMode = input.qualityGate === "pass"
    ? `Quality gate is disabled: normalize every in-scope request into the leanest model-appropriate execution brief. Selected quality gate: ${input.gate.toUpperCase()}.`
    : `Prompt Optimizer preflight. Selected quality gate: ${input.gate.toUpperCase()}.`
  const preservation = "Preserve the user's intent, language, exact literals, explicit constraints, requested output, and authorized scope. Do not invent requirements or request hidden reasoning instructions."
  sections.push({ id: "preservation", text: `${gateMode} ${preservation}` })
  sections.push({ id: "execution-mode", text: input.behavior === "preview" ? PREVIEW : "AUTO MODE: apply this execution brief internally and proceed in the same user turn. Do not print a rewritten prompt unless requested." })
  sections.push({ id: "objective", text: "Objective: fulfill the user's requested outcome as stated. The original user message remains authoritative; preserve its exact literals, scope, constraints, and requested deliverable." })
  const policy = taskPolicy(input.taskType, analysis)
  if (policy.length) sections.push({ id: "task-policy", text: `Task guidance:\n- ${policy.join("\n- ")}` })
  if (!analysis.hasValidation || input.gate === "full") sections.push({ id: "validation", text: "Validation: perform proportionate checks for the affected result and report what was verified; do not expand into unrelated testing." })
  if (analysis.consequential) sections.push({ id: "approval", text: "Approval boundary: confirm destructive, irreversible, external, production, credential-sensitive, or materially scope-expanding actions unless the user explicitly authorized them." })
  if (input.gate === "full") sections.push({ id: "sequence", text: analysis.readOnly
    ? "Execution sequence: resolve only the context needed to answer; inspect the requested scope; distinguish evidence from assumptions; validate the answer; stop when the requested deliverable is supported."
    : "Execution sequence: resolve only the context needed to act; perform the smallest in-scope work; inspect the result; fix issues caused by the change; validate; stop when completion criteria are met." })
  sections.push({ id: "completion", text: "Completion: report the outcome, changed or inspected scope, validation evidence, and any concrete blocker or remaining uncertainty." })
  if (input.profile !== "generic" && PROFILE_HINTS[input.profile]) sections.push({ id: "profile", text: PROFILE_HINTS[input.profile] })
  const lifecycleSettings = input.settings ?? { scope: "all", behavior: input.behavior, qualityGate: input.qualityGate, unsupportedModel: "generic" }
  sections.push({ id: "lifecycle", text: buildLifecycle(lifecycleSettings) })
  return { ...input, analysis, sections }
}

export function renderPromptPlan(plan: PromptPlan): string {
  if (!plan.sections.length) return ""
  const seen = new Set<string>()
  const sections = plan.sections.filter(section => {
    if (!section.text.trim() || seen.has(section.id)) return false
    seen.add(section.id)
    return true
  })
  const render = (items: typeof sections) => items.map(section => section.text.trim()).join("\n\n")
  let rendered = render(sections)
  if (rendered.length <= 5000) return rendered
  const optional = new Set(["profile", "lifecycle", "completion"])
  rendered = render(sections.filter(section => !optional.has(section.id)))
  if (rendered.length <= 5000) return rendered
  return render(sections.filter(section => !optional.has(section.id) && section.id !== "sequence"))
}
