import { Plugin } from "@opencode-ai/plugin"
import { existsSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

type Behavior = "auto" | "preview" | "off"
type Scope = "first" | "all"
type LegacyMode = "first" | "all" | "off"
type Profile =
  | "astra" | "sol" | "terra" | "luna"
  | "glm-5.2" | "glm-5.3" | "glm-5.3-flash"
  | "deepseek-v4-flash" | "deepseek-v4-pro"
  | "claude-fable-5.1" | "claude-fable-5" | "claude-opus-5" | "claude-opus-4.8" | "claude-sonnet-5"
  | "kimi-k3" | "muse-spark-1.3" | "hy4-preview" | "qwen3.8-max" | "gemini-3.8-flash" | "grok-4.6"

type Settings = { behavior: Behavior; scope: Scope; qualityGate: boolean; unsupportedModel: "skip" | "generic" }
type SessionState = { userPromptCount: number; candidateUserPromptCount?: number; active: boolean }

const DEFAULT_SETTINGS: Settings = { behavior: "auto", scope: "all", qualityGate: true, unsupportedModel: "skip" }

const BASE_COMMON = `Preserve the user's intent, language, exact literals, hard constraints, requested output, project rules, required verification and approval boundaries. Do not invent requirements. Resolve shorthand from relevant conversation/repository context without copying irrelevant history. State instructions once and keep the final execution brief as short as the task/model permits. For implementation, do authorized in-scope local work and proportionate non-destructive validation; confirm destructive, irreversible, external, costly, credential/security-sensitive or materially scope-expanding actions unless already authorized. Native Reasoning First: never request hidden chain-of-thought or inject generic 'think step by step/think harder/show reasoning' scaffolding. User instructions outrank this preflight.`
const BASE_GATE = `Prompt Optimizer v5.4 preflight. Apply a positive-value quality gate before acting: PASS if the user's request is already precise; LIGHT if only scope/constraint/done criteria need normalization; FULL only for genuinely complex/ambiguous work. ${BASE_COMMON}`
const BASE_ALWAYS = `Prompt Optimizer v5.4 preflight. Quality gate is disabled: normalize every in-scope user request into the leanest model-appropriate execution brief before acting, without adding requirements or unnecessary structure. ${BASE_COMMON}`

const PREVIEW = `PREVIEW MODE. Before any mutating or external action, build the exact optimized execution prompt for this user-turn. Read-only inspection is allowed only when necessary to resolve references. If the OpenCode question tool is available and this user-turn does not already contain an approved Prompt preview, call it exactly once with header "Prompt preview". Put the exact optimized prompt in the question text. Put option "Выполнить" first/default and option "Изменить" second; custom input is allowed. If approved, execute the previewed brief without asking again. If the user edits/customizes it, treat the edited version as source of truth. If the question tool is unavailable, print the optimized prompt and stop for explicit confirmation. Never pretend approval occurred.`
const AUTO_GATE = `AUTO MODE. Optimize internally only when the quality gate says it helps, keep the rewritten brief hidden, and execute immediately in this same user-turn.`
const AUTO_ALWAYS = `AUTO MODE. Normalize the in-scope request internally using the selected model profile, keep the rewritten brief hidden, and execute immediately in this same user-turn.`
const GENERIC = `Neutral fallback profile. Use only model/provider-neutral shaping; do not assume provider-specific reasoning, sampling, tool-history or cache behavior.`

const PROFILE_HINTS: Record<Profile, string> = {
  astra: "GPT-6 Astra: emphasize initiative/follow-through, explicit instruction priority and authorization boundaries; avoid unnecessary approval pauses and exhaustive generic testing; specify output style only when needed.",
  sol: "GPT-5.6 Sol: lean prompt, decisive context, hard constraints, autonomy/approval boundaries and success criteria; state each instruction once, focused tools, proportionate verification.",
  terra: "GPT-5.6 Terra: same official GPT-5.6 lean rules; compact complete brief and balanced context density. Tier-specific compactness is heuristic, never drop correctness-critical context.",
  luna: "GPT-5.6 Luna: same official GPT-5.6 lean rules; prefer the leanest bounded brief for high-volume efficiency without removing decisive constraints/context.",
  "glm-5.2": "GLM-5.2: for substantial engineering inspect architecture/dependencies/interfaces/affected scope, use a short execution-validation plan when useful, then implement and run relevant checks; apply GLM delimiters/examples/reference-output practices only when useful.",
  "glm-5.3": "GLM-5.3: goal + relevant context + hard constraints + acceptance criteria + autonomous end-to-end execution; avoid rigid microstep lists and manual CoT triggers.",
  "glm-5.3-flash": "GLM-5.3-Flash: GLM-5.3 framing; for visual/multimodal tasks use inspect/reference -> implement -> run/render -> compare actual output -> refine -> verify, and map multiple references to roles.",
  "deepseek-v4-flash": "DeepSeek V4 Flash: compact direct task/context/constraints/required verification/done criteria; no role-play/tool narration or manual CoT; reasoning history belongs to harness.",
  "deepseek-v4-pro": "DeepSeek V4 Pro: complete hard-task objective/context/requirements/scope/non-negotiable constraints/acceptance criteria; autonomous investigation/debugging/validation; avoid unrelated changes and manual CoT.",
  "claude-fable-5.1": "Claude Fable 5.1: Fable end-to-end framing plus targeted edits over whole-file rewrites, batch independent tool calls, explicit search trigger at low effort when evidence matters, scope/test guardrails, progress-update cadence only when useful; use Claude XML/examples/long-context ordering conditionally.",
  "claude-fable-5": "Claude Fable 5: objective/why/context/boundaries/acceptance with strong autonomy; ground progress in tool evidence; on genuinely long runs add periodic spec-based verification/fresh-context verifier when useful; prevent unrelated scope; remove legacy microsteps/reasoning extraction.",
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

function normalizeBehavior(v: unknown): Behavior | undefined { return v === "auto" || v === "preview" || v === "off" ? v : undefined }
function normalizeScope(v: unknown): Scope | undefined { return v === "first" || v === "all" ? v : undefined }
function normalizeLegacyMode(v: unknown): LegacyMode | undefined { return v === "first" || v === "all" || v === "off" ? v : undefined }
function readJson(path: string): Record<string, unknown> | undefined {
  if (!existsSync(path)) return undefined
  try { const p = JSON.parse(readFileSync(path, "utf8")); return p && typeof p === "object" && !Array.isArray(p) ? p : undefined } catch { return undefined }
}

function hasInvalidJson(path: string): boolean {
  if (!existsSync(path)) return false
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    return !value || typeof value !== "object" || Array.isArray(value)
  } catch {
    return true
  }
}

function hasInvalidManagedFields(value: Record<string, unknown> | undefined): boolean {
  if (!value) return false
  return (
    ("behavior" in value && !["auto", "preview", "off"].includes(String(value.behavior)))
    || ("scope" in value && !["first", "all"].includes(String(value.scope)))
    || ("qualityGate" in value && typeof value.qualityGate !== "boolean")
    || ("unsupportedModel" in value && !["skip", "generic"].includes(String(value.unsupportedModel)))
    || ("mode" in value && !["first", "all", "off"].includes(String(value.mode)))
  )
}

export function detectProfile(providerID: string, modelID: string): Profile | undefined {
  const id = `${providerID}/${modelID}`.toLowerCase().replace(/_/g, "-")
  if (/claude.*fable[^a-z0-9]*5[.-]1(?:$|[^a-z0-9])/.test(id) || id.includes("claude-fable-5.1") || id.includes("claude-fable-5-1")) return "claude-fable-5.1"
  if (/claude.*fable[^a-z0-9]*5(?:$|[^a-z0-9])/.test(id) || id.includes("claude-fable-5")) return "claude-fable-5"
  if (/claude.*opus[^a-z0-9]*4[.-]8(?:$|[^a-z0-9])/.test(id) || id.includes("claude-opus-4.8") || id.includes("claude-opus-4-8")) return "claude-opus-4.8"
  if (/claude.*opus[^a-z0-9]*5(?:$|[^a-z0-9])/.test(id) || id.includes("claude-opus-5")) return "claude-opus-5"
  if (/claude.*sonnet[^a-z0-9]*5(?:$|[^a-z0-9])/.test(id) || id.includes("claude-sonnet-5")) return "claude-sonnet-5"
  if (/kimi.*k[^a-z0-9]*3(?:$|[^a-z0-9])/.test(id) || id.includes("kimi-k3")) return "kimi-k3"
  if (/muse.*spark[^a-z0-9]*1[.-]3(?:$|[^a-z0-9])/.test(id) || id.includes("muse-spark-1.3")) return "muse-spark-1.3"
  if (/hy[^a-z0-9]*4.*preview/.test(id) || id.includes("hy4-preview")) return "hy4-preview"
  if (/qwen[^a-z0-9]*3[.-]8.*max/.test(id) || id.includes("qwen3.8-max") || id.includes("qwen-3.8-max")) return "qwen3.8-max"
  if (/gemini[^a-z0-9]*3[.-]8.*flash/.test(id) || id.includes("gemini-3.8-flash")) return "gemini-3.8-flash"
  if (/grok[^a-z0-9]*4[.-]6(?:$|[^a-z0-9])/.test(id) || id.includes("grok-4.6")) return "grok-4.6"
  if (/glm[^a-z0-9]*5[.-]3[^a-z0-9]*flash/.test(id) || id.includes("glm-5.3-flash")) return "glm-5.3-flash"
  if (/glm[^a-z0-9]*5[.-]3(?:$|[^a-z0-9])/.test(id) || id.includes("glm-5.3")) return "glm-5.3"
  if (/glm[^a-z0-9]*5[.-]2(?:$|[^a-z0-9])/.test(id) || id.includes("glm-5.2")) return "glm-5.2"
  if (/deepseek.*(?:v[^a-z0-9]*)?4.*flash/.test(id)) return "deepseek-v4-flash"
  if (/deepseek.*(?:v[^a-z0-9]*)?4.*pro/.test(id)) return "deepseek-v4-pro"
  if (id.includes("gpt-6-astra") || /(^|[/._-])astra($|[/._-])/.test(id)) return "astra"
  if (id.includes("gpt-5.6-terra") || id.includes("5.6-terra") || /(^|[/._-])terra($|[/._-])/.test(id)) return "terra"
  if (id.includes("gpt-5.6-luna") || id.includes("5.6-luna") || /(^|[/._-])luna($|[/._-])/.test(id)) return "luna"
  if (id.includes("gpt-5.6-sol") || id.includes("5.6-sol") || /(^|[/._-])sol($|[/._-])/.test(id)) return "sol"
  if (/(^|[/._-])gpt-5\.6($|[/])/i.test(id)) return "sol"
  return undefined
}

function countPriorUserMessages(messages: readonly unknown[]): number {
  let count = 0
  for (const entry of messages as readonly any[]) {
    const role = entry?.role ?? entry?.message?.role ?? entry?.info?.role
    if (role === "user") count++
  }
  return count
}

export default Plugin.define({
  id: "prompt-optimizer-v5-4",
  async setup(ctx) {
    const projectRoot = ctx.location.project?.directory ?? ctx.location.directory
    const sharedProject = join(projectRoot, ".prompt-optimizer.json")
    const sharedGlobal = join(homedir(), ".config", "prompt-optimizer", "config.json")
    const projectConfig = join(projectRoot, ".opencode", "prompt-optimizer.json")
    const globalConfig = join(homedir(), ".config", "opencode", "prompt-optimizer.json")

    const loadSettings = (): Settings => {
      const files = [readJson(sharedGlobal) ?? {}, readJson(globalConfig) ?? {}, readJson(sharedProject) ?? {}, readJson(projectConfig) ?? {}]
      if ([sharedGlobal, globalConfig, sharedProject, projectConfig].some(path => hasInvalidJson(path) || hasInvalidManagedFields(readJson(path)))) {
        return { ...DEFAULT_SETTINGS, behavior: "off" }
      }
      const merged = Object.assign({}, ...files, (ctx.options ?? {}) as Record<string, unknown>)
      const legacy = normalizeLegacyMode(merged.mode ?? process.env.OPENCODE_PROMPT_OPTIMIZER_MODE)
      const behavior = normalizeBehavior(process.env.PROMPT_OPTIMIZER_BEHAVIOR) ?? normalizeBehavior(merged.behavior) ?? (legacy === "off" ? "off" : DEFAULT_SETTINGS.behavior)
      const scope = normalizeScope(process.env.PROMPT_OPTIMIZER_SCOPE) ?? normalizeScope(merged.scope) ?? (legacy === "first" || legacy === "all" ? legacy : DEFAULT_SETTINGS.scope)
      const unsupportedRaw = process.env.PROMPT_OPTIMIZER_UNSUPPORTED_MODEL ?? merged.unsupportedModel
      const qEnv = process.env.PROMPT_OPTIMIZER_QUALITY_GATE
      const qualityGate = qEnv === undefined
        ? (typeof merged.qualityGate === "boolean" ? merged.qualityGate : true)
        : ["false", "off", "0"].includes(qEnv.toLowerCase()) ? false : true
      return { behavior, scope, qualityGate, unsupportedModel: unsupportedRaw === "generic" ? "generic" : "skip" }
    }

    const stateKey = (sessionID: string) => `prompt-optimizer/session/${sessionID}`

    await ctx.session.hook("prompt", async (event) => {
      const settings = loadSettings()
      const key = stateKey(event.sessionID)
      const stored = (await ctx.storage.get(key)) as SessionState | undefined
      let priorCount = stored?.userPromptCount
      if (priorCount === undefined) {
        try { priorCount = countPriorUserMessages(await ctx.session.context({ sessionID: event.sessionID })) } catch { priorCount = 0 }
      }
       const candidateUserPromptCount = priorCount + 1
       const inScope = settings.scope === "all" || (settings.scope === "first" && priorCount === 0)
       await ctx.storage.set(key, { userPromptCount: priorCount, candidateUserPromptCount, active: settings.behavior !== "off" && inScope })
    })

    await ctx.session.hook("context", async (event) => {
      if (event.agent === "compaction") return
      const state = (await ctx.storage.get(stateKey(event.sessionID))) as SessionState | undefined
      if (!state?.active) return
       const settings = loadSettings()
       if (settings.behavior === "off") return
       const profile = detectProfile(event.model.providerID, event.model.id)
       if (!profile && settings.unsupportedModel === "skip") {
         await ctx.storage.set(stateKey(event.sessionID), { userPromptCount: state.userPromptCount, active: false })
         return
       }
       const admittedCount = state.candidateUserPromptCount ?? state.userPromptCount
       await ctx.storage.set(stateKey(event.sessionID), { userPromptCount: admittedCount, active: true })
      const hint = profile ? PROFILE_HINTS[profile] : GENERIC
      const base = settings.qualityGate ? BASE_GATE : BASE_ALWAYS
      const behavior = settings.behavior === "preview" ? PREVIEW : (settings.qualityGate ? AUTO_GATE : AUTO_ALWAYS)
      event.system.push({ text: `${base}\n${hint}\n${behavior}\nLifecycle: this instruction is bound to the current admitted user-turn. scope=${settings.scope}; behavior=${settings.behavior}; qualityGate=${settings.qualityGate}. Tool continuations remain in the same turn and must not create a second preview.` })
    })
  },
})
