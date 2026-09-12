import { classifyTask } from "./task-classifier"
import { buildLifecycle, GENERIC, BASE_ALWAYS, BASE_GATE, PREVIEW, PROFILE_HINTS as PROFILE_HINTS_DATA } from "./prompt-builder"
import { resolveSettings, configSourceLabel } from "./config"
import { decide } from "./decision-engine"
import { emptyMetrics, hashPrompt, incrementMetrics, isDuplicate } from "./session-state"
import type { SessionOverride, SessionState } from "./types"

// Keep the registry-facing union in this entrypoint so the existing conformance
// check can detect missing OpenCode profile routing without importing TypeScript.
type Profile =
  | "astra" | "sol" | "terra" | "luna"
  | "glm-5.2" | "glm-5.3" | "glm-5.3-flash"
  | "deepseek-v4-flash" | "deepseek-v4-pro"
  | "claude-fable-5.1" | "claude-fable-5" | "claude-opus-5" | "claude-opus-4.8" | "claude-sonnet-5"
  | "kimi-k3" | "muse-spark-1.3" | "hy4-preview" | "qwen3.8-max" | "gemini-3.8-flash" | "grok-4.6"

type Settings = import("./types").Settings

const PROFILE_HINTS: Record<Profile, string> = {
  astra: PROFILE_HINTS_DATA.astra,
  sol: PROFILE_HINTS_DATA.sol,
  terra: PROFILE_HINTS_DATA.terra,
  luna: PROFILE_HINTS_DATA.luna,
  "glm-5.2": PROFILE_HINTS_DATA["glm-5.2"],
  "glm-5.3": PROFILE_HINTS_DATA["glm-5.3"],
  "glm-5.3-flash": PROFILE_HINTS_DATA["glm-5.3-flash"],
  "deepseek-v4-flash": PROFILE_HINTS_DATA["deepseek-v4-flash"],
  "deepseek-v4-pro": PROFILE_HINTS_DATA["deepseek-v4-pro"],
  "claude-fable-5.1": PROFILE_HINTS_DATA["claude-fable-5.1"],
  "claude-fable-5": PROFILE_HINTS_DATA["claude-fable-5"],
  "claude-opus-5": PROFILE_HINTS_DATA["claude-opus-5"],
  "claude-opus-4.8": PROFILE_HINTS_DATA["claude-opus-4.8"],
  "claude-sonnet-5": PROFILE_HINTS_DATA["claude-sonnet-5"],
  "kimi-k3": PROFILE_HINTS_DATA["kimi-k3"],
  "muse-spark-1.3": PROFILE_HINTS_DATA["muse-spark-1.3"],
  "hy4-preview": PROFILE_HINTS_DATA["hy4-preview"],
  "qwen3.8-max": PROFILE_HINTS_DATA["qwen3.8-max"],
  "gemini-3.8-flash": PROFILE_HINTS_DATA["gemini-3.8-flash"],
  "grok-4.6": PROFILE_HINTS_DATA["grok-4.6"],
}

const AUTO_GATE = "AUTO MODE. Optimize internally only when the quality gate says it helps, keep the rewritten brief hidden, and execute immediately in this same user-turn."
const AUTO_ALWAYS = "AUTO MODE. Normalize the in-scope request internally using the selected model profile, keep the rewritten brief hidden, and execute immediately in this same user-turn."

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

function stateKey(sessionID: string): string {
  return `prompt-optimizer/session/${sessionID}`
}

function promptText(event: any): string | undefined {
  const candidates = [
    event?.prompt,
    event?.text,
    event?.message?.content,
    event?.message?.text,
    ...(Array.isArray(event?.parts) ? event.parts.map((part: any) => part?.type === "text" ? part.text : undefined) : []),
  ]
  const value = candidates.find(item => typeof item === "string" && item.trim())
  return typeof value === "string" ? value : undefined
}

function mergeState(previous: SessionState | undefined, patch: Partial<SessionState>): SessionState {
  return {
    userPromptCount: previous?.userPromptCount ?? 0,
    candidateUserPromptCount: previous?.candidateUserPromptCount,
    active: previous?.active ?? false,
    metrics: previous?.metrics ?? emptyMetrics(),
    ...previous,
    ...patch,
  }
}

type RuntimeSession = {
  state: SessionState
  pendingPrompt?: string
  pendingMessageId?: string
}

function settingLine(name: string, value: string, source: string): string {
  return `${name}: ${value} (${source})`
}

function statusText(settings: ReturnType<typeof resolveSettings>, state: SessionState | undefined, model?: { providerID?: string; id?: string }): string {
  const metrics = state?.metrics ?? emptyMetrics()
  const profile = model?.providerID && model.id ? detectProfile(model.providerID, model.id) : undefined
  return [
    "Prompt Optimizer",
    "",
    settingLine("Status", settings.behavior === "off" ? "OFF" : "ENABLED", settings.invalidConfig ? "invalid config" : "resolved"),
    settingLine("Mode", settings.behavior.toUpperCase(), configSourceLabel(settings.sources.behavior)),
    settingLine("Scope", settings.scope.toUpperCase(), configSourceLabel(settings.sources.scope)),
    settingLine("Quality gate", settings.qualityGate.toUpperCase(), configSourceLabel(settings.sources.qualityGate)),
    settingLine("Model", model?.providerID && model.id ? `${model.providerID}/${model.id}` : "not resolved", "OpenCode"),
    settingLine("Profile", profile ?? (settings.unsupportedModel === "generic" ? "GENERIC" : "NONE"), profile ? "registry" : "fallback"),
    "",
    `Session: ${metrics.processed} processed · ${metrics.optimized} optimized · ${metrics.skipped} skipped`,
    `Gates: PASS ${metrics.pass} · LIGHT ${metrics.light} · FULL ${metrics.full}`,
    settings.invalidConfig ? "Warning: invalid managed configuration forced safe OFF mode." : "",
  ].filter(Boolean).join("\n")
}

export function formatDecision(decision: ReturnType<typeof decide>, settings: ReturnType<typeof resolveSettings>, state?: SessionState): string {
  const metrics = state?.metrics ?? emptyMetrics()
  return [
    "Prompt Optimizer decision",
    "",
    `Action: ${decision.action.toUpperCase()}`,
    `Mode: ${decision.behavior.toUpperCase()}`,
    `Profile: ${decision.profile.toUpperCase()}`,
    `Task: ${decision.taskType}`,
    `Quality gate: ${(decision.gate ?? decision.qualityGate).toUpperCase()}`,
    `Confidence: ${decision.profileConfidence}`,
    `Reason: ${decision.reason}`,
    decision.warning ? `Warning: ${decision.warning}` : "",
    `Session totals: ${metrics.processed} processed, ${metrics.optimized} optimized, ${metrics.skipped} skipped`,
    settings.invalidConfig ? "Config status: invalid; safe OFF fallback is active." : "Config status: valid",
  ].filter(Boolean).join("\n")
}

const server = async (ctx: any, options?: Record<string, unknown>) => {
  const projectRoot = typeof ctx?.directory === "string" ? ctx.directory : process.cwd()
  const sessions = new Map<string, RuntimeSession>()
  const loadSettings = () => resolveSettings(projectRoot, options)
  const getSession = (sessionID: string): RuntimeSession => sessions.get(sessionID) ?? {
    state: { userPromptCount: 0, active: false, metrics: emptyMetrics() },
  }

  return {
    "chat.message": async (input: any, output: any) => {
      const key = stateKey(input.sessionID)
      const current = getSession(key)
      const stored = current.state
      const priorCount = stored.userPromptCount
      const prompt = promptText({ message: output?.message, parts: output?.parts })
      const settings = loadSettings()
      const effectiveBehavior = stored.override?.behavior ?? settings.behavior
      const effectiveScope = stored.override?.scope ?? settings.scope
      const inScope = effectiveScope === "all" || (effectiveScope === "first" && priorCount === 0)
      const next = mergeState(stored, {
        userPromptCount: priorCount + 1,
        candidateUserPromptCount: priorCount + 1,
        active: effectiveBehavior !== "off" && inScope,
        pendingPromptHash: prompt ? hashPrompt(prompt) : undefined,
      })
      sessions.set(key, { state: next, pendingPrompt: prompt, pendingMessageId: input.messageID })
    },

    "experimental.chat.system.transform": async (input: any, output: any) => {
      const key = stateKey(input.sessionID ?? "__default__")
      const current = getSession(key)
      const stored = current.state
      const prompt = current.pendingPrompt
      if (!stored.active || !prompt) return
      if (current.pendingMessageId && stored.lastProcessedEventId === current.pendingMessageId) return

      const settings = loadSettings()
      const effectiveSettings: Settings = {
        ...settings,
        ...stored.override,
        behavior: stored.override?.behavior ?? settings.behavior,
        scope: stored.override?.scope ?? settings.scope,
        qualityGate: stored.override?.qualityGate ?? settings.qualityGate,
      }
      if (effectiveSettings.behavior === "off") return
      const model = {
        providerID: String(input.model?.providerID ?? ""),
        modelID: String(input.model?.id ?? input.model?.modelID ?? ""),
      }
      const profile = stored.override?.profile && stored.override.profile !== "auto" && stored.override.profile !== "generic"
        ? stored.override.profile
        : detectProfile(model.providerID, model.modelID)
      const task = classifyTask(prompt)
      const duplicate = !current.pendingPrompt && isDuplicate(stored, current.pendingMessageId, prompt)
      const decision = !profile && effectiveSettings.unsupportedModel === "skip"
        ? { action: "skip" as const, behavior: effectiveSettings.behavior, scope: effectiveSettings.scope, qualityGate: effectiveSettings.qualityGate, taskType: task.type, profile: "none" as const, profileConfidence: "low" as const, reason: "model is not in the registry" }
        : decide({
          settings: effectiveSettings,
          scopeEligible: true,
          model,
          profile,
          sessionOverride: stored.override,
          duplicate,
          taskType: task.type,
        }, prompt)
      const nextMetrics = incrementMetrics(stored, decision.action, decision.profile, decision.gate)
      const nextState = mergeState(stored, {
        active: decision.action !== "skip" || effectiveSettings.scope === "all",
        lastModel: model,
        lastTaskType: task.type,
        metrics: nextMetrics,
        lastProcessedEventId: current.pendingMessageId ?? stored.lastProcessedEventId,
        lastPromptHash: hashPrompt(prompt),
        pendingPromptHash: undefined,
        lastDecision: decision,
      })
      sessions.set(key, { state: nextState })
      if (decision.action === "skip") return

      const hint = decision.profile === "generic" ? GENERIC : PROFILE_HINTS[decision.profile as Profile]
      const base = effectiveSettings.qualityGate === "pass" ? BASE_ALWAYS : BASE_GATE
      const behaviorText = decision.behavior === "preview" ? PREVIEW : (effectiveSettings.qualityGate === "pass" ? AUTO_ALWAYS : AUTO_GATE)
      output.system.push(`${base}\n${hint}\n${behaviorText}\n${buildLifecycle(effectiveSettings)}\n${formatDecision(decision, settings, stored)}`)
    },

    "command.execute.before": async (input: any, output: any) => {
      const command = String(input.command ?? "").replace(/^\/+/, "").toLowerCase()
      if (command !== "prompt-optimizer" && command !== "po" && command !== "po-status") return
      const key = stateKey(input.sessionID)
      const current = getSession(key)
      const settings = loadSettings()
      const argument = String(input.arguments ?? "").trim().toLowerCase()
      const tokens = argument.split(/\s+/).filter(Boolean)
      const operation = command === "po-status" ? "status" : tokens[0] ?? "status"
      const override: SessionOverride = { ...(current.state.override ?? {}) }
      if (operation === "reset") current.state.override = undefined
      else if (operation === "on" || operation === "auto") override.behavior = "auto"
      else if (operation === "off") override.behavior = "off"
      else if (operation === "preview") override.behavior = "preview"
      else if (operation === "first" || operation === "all") override.scope = operation
      else if (operation === "pass" || operation === "light" || operation === "full" || operation === "adaptive") override.qualityGate = operation
      else if (!["status", "explain"].includes(operation)) return
      if (operation !== "status" && operation !== "explain" && operation !== "reset") current.state.override = override
      if (operation === "status") {
        const model = current.state.lastModel ? { providerID: current.state.lastModel.providerID, id: current.state.lastModel.modelID } : undefined
        output.parts.push({ type: "text", text: statusText(resolveSettings(projectRoot, { ...options, ...current.state.override }), current.state, model) })
      } else if (operation === "explain") {
        const decision = current.state.lastDecision
        output.parts.push({ type: "text", text: decision ? `Prompt Optimizer decision\n\nAction: ${decision.action.toUpperCase()}\nProfile: ${decision.profile.toUpperCase()}\nGate: ${(decision.gate ?? "not selected").toUpperCase()}\nReason: ${decision.reason}` : "Prompt Optimizer has no decision for this session yet." })
      } else {
        sessions.set(key, current)
        output.parts.push({ type: "text", text: `Prompt Optimizer session override: ${operation}. Persistent configuration was not changed.` })
      }
    },
  }
}

export default { id: "prompt-optimizer-v5-5", server }
