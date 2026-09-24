import { classifyTask } from "./task-classifier"
import { buildLifecycle, GENERIC, BASE_ALWAYS, BASE_GATE, PREVIEW, PROFILE_HINTS, qualityText } from "./prompt-builder"
import { resolveSettings, configSourceLabel } from "./config"
import { decide } from "./decision-engine"
import { emptyMetrics, hashPrompt, incrementMetrics, pruneSessions } from "./session-state"
import { EXACT_MODEL_ALIASES } from "./model-registry"
import type { ModelResolution, Profile, SessionOverride, SessionState } from "./types"

// Universal Prompt Optimizer v5.6

type Settings = import("./types").Settings

const AUTO_GATE = "AUTO MODE. Optimize internally only when the quality gate says it helps, keep the rewritten brief hidden, and execute immediately in this same user-turn."
const AUTO_ALWAYS = "AUTO MODE. Normalize the in-scope request internally using the selected model profile, keep the rewritten brief hidden, and execute immediately in this same user-turn."


function normalizeModelID(value: string): string {
  return value.trim().toLowerCase().replace(/_/g, "-")
}

function modelCandidates(modelID: string): string[] {
  const normalized = normalizeModelID(modelID)
  const leaf = normalized.split("/").at(-1) ?? normalized
  const candidates = [normalized, leaf]
  if (leaf.endsWith("-latest")) candidates.push(leaf.slice(0, -"-latest".length))
  return [...new Set(candidates)]
}

function matchedModel(modelID: string): { profile: Profile; alias: string } | undefined {
  for (const candidate of modelCandidates(modelID)) {
    const profile = Object.hasOwn(EXACT_MODEL_ALIASES, candidate) ? EXACT_MODEL_ALIASES[candidate] : undefined
    if (profile) return { profile, alias: candidate }
  }
  return undefined
}

export function detectProfile(_providerID: string, modelID: string): Profile | undefined {
  // Only the model ID is authoritative. Provider names are not model aliases.
  return matchedModel(modelID)?.profile
}

export function resolveModel(providerID: string, modelID: string): ModelResolution {
  const normalizedModelID = normalizeModelID(modelID)
  const exactMatch = matchedModel(modelID)
  if (exactMatch) {
    return {
      profile: exactMatch.profile,
      confidence: "high",
      source: exactMatch.alias === normalizedModelID ? "exact-id" : "pattern",
      modelID: normalizedModelID,
      matchedAlias: exactMatch.alias,
    }
  }
  return {
    confidence: "low",
    source: "unsupported",
    modelID: normalizedModelID,
  }
}

export function formatModelResolution(resolution: ModelResolution): string {
  const profile = resolution.profile ?? "none"
  const alias = resolution.matchedAlias ? `, alias=${resolution.matchedAlias}` : ""
  return `${profile} (${resolution.source}, confidence=${resolution.confidence}${alias})`
}

function stateKey(sessionID: string): string {
  return `prompt-optimizer/session/${sessionID}`
}

function sessionIDOf(value: unknown): string {
  return typeof value === "string" && value.trim() ? value : "__default__"
}

export function promptText(event: any): string | undefined {
  const parts = Array.isArray(event?.parts)
    ? event.parts
      .filter((part: any) => part?.type === "text" && typeof part.text === "string" && part.text.trim())
      .map((part: any) => part.text.trim())
    : []
  if (parts.length) return parts.join("\n\n")

  const candidates = [event?.prompt, event?.text, event?.message?.content, event?.message?.text]
  const value = candidates.find(item => typeof item === "string" && item.trim())
  return typeof value === "string" ? value.trim() : undefined
}

function mergeState(previous: SessionState | undefined, patch: Partial<SessionState>): SessionState {
  return {
    userPromptCount: previous?.userPromptCount ?? 0,
    candidateUserPromptCount: previous?.candidateUserPromptCount,
    active: previous?.active ?? false,
    lastSeenAt: previous?.lastSeenAt,
    lastResolution: previous?.lastResolution,
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
  const resolution = model?.providerID && model.id ? resolveModel(model.providerID, model.id) : state?.lastResolution
  const profile = resolution?.profile
  return [
    "Prompt Optimizer",
    "",
    settingLine("Status", settings.behavior === "off" ? "OFF" : "ENABLED", settings.invalidConfig ? "invalid config" : "resolved"),
    settingLine("Mode", settings.behavior.toUpperCase(), configSourceLabel(settings.sources.behavior)),
    settingLine("Scope", settings.scope.toUpperCase(), configSourceLabel(settings.sources.scope)),
    settingLine("Quality gate", settings.qualityGate.toUpperCase(), configSourceLabel(settings.sources.qualityGate)),
    settingLine("Model", model?.providerID && model.id ? `${model.providerID}/${model.id}` : "not resolved", "OpenCode"),
    settingLine("Profile", profile ?? (settings.unsupportedModel === "generic" ? "GENERIC" : "NONE"), profile ? `${resolution?.source ?? "registry"}${resolution?.matchedAlias ? `:${resolution.matchedAlias}` : ""}` : "fallback"),
    settingLine("Preview", "advisory (model-guided)", "OpenCode v1"),
    resolution ? settingLine("Resolution", formatModelResolution(resolution), "diagnostic") : "",
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
    state?.lastResolution ? `Model resolution: ${formatModelResolution(state.lastResolution)}` : "",
    "Preview enforcement: advisory (OpenCode v1 model-guided flow)",
    decision.warning ? `Warning: ${decision.warning}` : "",
    `Session totals: ${metrics.processed} processed, ${metrics.optimized} optimized, ${metrics.skipped} skipped`,
    settings.invalidConfig ? "Config status: invalid; safe OFF fallback is active." : "Config status: valid",
  ].filter(Boolean).join("\n")
}

const server = async (ctx: any, options?: Record<string, unknown>) => {
  const projectRoot = typeof ctx?.directory === "string" ? ctx.directory : process.cwd()
  const sessions = new Map<string, RuntimeSession>()
  const loadSettings = () => resolveSettings(projectRoot, options)
  const getSession = (sessionID: string): RuntimeSession => {
    const current = sessions.get(sessionID)
    if (current) return current
    return { state: { userPromptCount: 0, active: false, metrics: emptyMetrics() } }
  }
  const touchSession = (key: string, session: RuntimeSession): void => {
    session.state.lastSeenAt = Date.now()
    sessions.set(key, session)
    pruneSessions(sessions)
  }

  return {
    "chat.message": async (input: any, output: any) => {
      const key = stateKey(sessionIDOf(input.sessionID))
      const current = getSession(key)
      const stored = current.state
      const messageID = typeof input.messageID === "string" ? input.messageID : undefined
      if (messageID && current.pendingMessageId === messageID) return
      const priorCount = stored.userPromptCount
      const prompt = promptText({ message: output?.message, parts: output?.parts })
      const settings = loadSettings()
      const effectiveBehavior = settings.invalidConfig ? "off" : stored.override?.behavior ?? settings.behavior
      const effectiveScope = stored.override?.scope ?? settings.scope
      const inScope = effectiveScope === "all" || (effectiveScope === "first" && priorCount === 0)
      const next = mergeState(stored, {
        candidateUserPromptCount: priorCount + 1,
        active: effectiveBehavior !== "off" && inScope,
         lastSeenAt: Date.now(),
         pendingPromptHash: prompt ? hashPrompt(prompt) : undefined,
       })
       touchSession(key, { state: next, pendingPrompt: prompt, pendingMessageId: messageID })
    },

    "experimental.chat.system.transform": async (input: any, output: any) => {
      const key = stateKey(sessionIDOf(input.sessionID))
      const current = getSession(key)
      const stored = current.state
      const prompt = current.pendingPrompt
      if (!stored.active || !prompt) return
      if (current.pendingMessageId && stored.lastProcessedEventId === current.pendingMessageId) return

      const settings = loadSettings()
      const effectiveSettings: Settings = {
        ...settings,
        ...stored.override,
        behavior: settings.invalidConfig ? "off" : stored.override?.behavior ?? settings.behavior,
        scope: stored.override?.scope ?? settings.scope,
        qualityGate: stored.override?.qualityGate ?? settings.qualityGate,
      }
      if (effectiveSettings.behavior === "off") return
      const scopeEligible = effectiveSettings.scope === "all" || stored.userPromptCount === 0
      if (!scopeEligible) return
      const model = {
        providerID: String(input.model?.providerID ?? ""),
        modelID: String(input.model?.id ?? input.model?.modelID ?? ""),
      }
      const resolution = stored.override?.profile && stored.override.profile !== "auto" && stored.override.profile !== "generic"
        ? { profile: stored.override.profile, confidence: "high" as const, source: "exact-id" as const, modelID: model.modelID }
        : resolveModel(model.providerID, model.modelID)
      const profile = resolution.profile
      const task = classifyTask(prompt)
      const decision = !profile && effectiveSettings.unsupportedModel === "skip"
        ? { action: "skip" as const, behavior: effectiveSettings.behavior, scope: effectiveSettings.scope, qualityGate: effectiveSettings.qualityGate, taskType: task.type, profile: "none" as const, profileConfidence: "low" as const, reason: "model is not in the registry" }
        : decide({
          settings: effectiveSettings,
          scopeEligible,
          model,
          profile,
          sessionOverride: stored.override,
          taskType: task.type,
          risk: task.risk,
          executionIntent: task.executionIntent,
        }, prompt)
      const nextMetrics = incrementMetrics(stored, decision.action, decision.profile, decision.gate)
      const processed = decision.action !== "skip"
      const nextUserPromptCount = processed ? stored.userPromptCount + 1 : stored.userPromptCount
      const nextState = mergeState(stored, {
        userPromptCount: nextUserPromptCount,
        active: effectiveSettings.scope === "all" || nextUserPromptCount === 0,
        lastModel: model,
        lastResolution: resolution,
        lastTaskType: task.type,
        metrics: nextMetrics,
        lastProcessedEventId: current.pendingMessageId ?? stored.lastProcessedEventId,
        lastPromptHash: hashPrompt(prompt),
        pendingPromptHash: undefined,
        lastDecision: decision,
      })
      touchSession(key, { state: nextState })
      if (decision.action === "skip") return

      // An adaptive PASS means the user's prompt is already sufficient. Keep the
      // decision observable without spending model context restating it.
      if (decision.behavior === "auto" && effectiveSettings.qualityGate === "adaptive" && decision.gate === "pass") return

      const hint = decision.profile === "generic" ? GENERIC : PROFILE_HINTS[decision.profile]
      const base = effectiveSettings.qualityGate === "pass" ? BASE_ALWAYS : BASE_GATE
      const behaviorText = decision.behavior === "preview" ? PREVIEW : (effectiveSettings.qualityGate === "pass" ? AUTO_ALWAYS : AUTO_GATE)
      const selectedGate = decision.gate ? `${qualityText(decision.gate)}\n` : ""
      output.system.push(`${base}\n${selectedGate}${hint}\n${behaviorText}\n${buildLifecycle(effectiveSettings)}`)
    },

    "command.execute.before": async (input: any, output: any) => {
      const command = String(input.command ?? "").replace(/^\/+/, "").toLowerCase()
      if (command !== "prompt-optimizer" && command !== "po" && command !== "po-status") return
      const key = stateKey(sessionIDOf(input.sessionID))
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
