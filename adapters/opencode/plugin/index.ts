import { Plugin } from "@opencode-ai/plugin"
import { classifyTask } from "./task-classifier"
import { buildLifecycle, GENERIC, BASE_ALWAYS, BASE_GATE, PREVIEW, PROFILE_HINTS as PROFILE_HINTS_DATA } from "./prompt-builder"
import { resolveSettings, configSourceLabel } from "./config"
import { decide } from "./decision-engine"
import { emptyMetrics, hashPrompt, incrementMetrics, isDuplicate, normalizeState } from "./session-state"
import type { SessionState } from "./types"

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

function countPriorUserMessages(messages: readonly unknown[]): number {
  let count = 0
  for (const entry of messages as readonly any[]) {
    const role = entry?.role ?? entry?.message?.role ?? entry?.info?.role
    if (role === "user") count++
  }
  return count
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

function stateKey(sessionID: string): string {
  return `prompt-optimizer/session/${sessionID}`
}

function promptText(event: any): string | undefined {
  const candidates = [event?.prompt, event?.text, event?.message?.content, event?.message?.text]
  const value = candidates.find(item => typeof item === "string" && item.trim())
  return typeof value === "string" ? value : undefined
}

function eventID(event: any): string | undefined {
  const value = event?.eventID ?? event?.eventId ?? event?.id ?? event?.messageID ?? event?.messageId
  return typeof value === "string" && value.trim() ? value : undefined
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

export default Plugin.define({
  id: "prompt-optimizer-v5-5",
  async setup(ctx) {
    const projectRoot = ctx.location.project?.directory ?? ctx.location.directory
    const loadSettings = () => resolveSettings(projectRoot, (ctx.options ?? {}) as Record<string, unknown>)

    await ctx.session.hook("prompt", async (event: any) => {
      const settings = loadSettings()
      const key = stateKey(event.sessionID)
      const stored = normalizeState(await ctx.storage.get(key))
      let priorCount = stored?.userPromptCount
      if (priorCount === undefined) {
        try { priorCount = countPriorUserMessages(await ctx.session.context({ sessionID: event.sessionID })) } catch { priorCount = 0 }
      }
      const candidateUserPromptCount = priorCount + 1
      const effectiveBehavior = stored?.override?.behavior ?? settings.behavior
      const effectiveScope = stored?.override?.scope ?? settings.scope
      const inScope = effectiveScope === "all" || (effectiveScope === "first" && priorCount === 0)
      const prompt = promptText(event)
      await ctx.storage.set(key, mergeState(stored, {
        userPromptCount: priorCount,
        candidateUserPromptCount,
        active: effectiveBehavior !== "off" && inScope,
        lastProcessedEventId: eventID(event),
        lastPromptHash: prompt ? hashPrompt(prompt) : stored?.lastPromptHash,
      }))
    })

    await ctx.session.hook("context", async (event: any) => {
      if (event.agent === "compaction") return
      const key = stateKey(event.sessionID)
      const stored = normalizeState(await ctx.storage.get(key))
      if (!stored?.active) return
      const settings = loadSettings()
      const effectiveSettings: Settings = {
        ...settings,
        ...stored.override,
        behavior: stored.override?.behavior ?? settings.behavior,
        scope: stored.override?.scope ?? settings.scope,
        qualityGate: stored.override?.qualityGate ?? settings.qualityGate,
      }
      if (effectiveSettings.behavior === "off") return
      const model = { providerID: String(event.model?.providerID ?? ""), modelID: String(event.model?.id ?? "") }
      const profile = stored.override?.profile && stored.override.profile !== "auto" && stored.override.profile !== "generic"
        ? stored.override.profile
        : detectProfile(model.providerID, model.modelID)
      if (!profile && effectiveSettings.unsupportedModel === "skip") {
        await ctx.storage.set(key, mergeState(stored, { active: false, lastDecision: { action: "skip", profile: "none", reason: "model is not in the registry" } }))
        return
      }
      const prompt = promptText(event) ?? ""
      const duplicate = isDuplicate(stored, eventID(event), prompt)
      const task = classifyTask(prompt)
      const decision = decide({
        settings: effectiveSettings,
        scopeEligible: true,
        model,
        profile,
        sessionOverride: stored.override,
        duplicate,
        taskType: task.type,
      }, prompt)
      const nextMetrics = incrementMetrics(stored, decision.action, decision.profile, decision.gate)
      await ctx.storage.set(key, mergeState(stored, {
        userPromptCount: stored.candidateUserPromptCount ?? stored.userPromptCount,
        active: decision.action !== "skip" || effectiveSettings.scope === "all",
        metrics: nextMetrics,
        lastProcessedEventId: eventID(event) ?? stored.lastProcessedEventId,
        lastPromptHash: prompt ? hashPrompt(prompt) : stored.lastPromptHash,
        lastDecision: decision,
      }))
      if (decision.action === "skip") {
        if (effectiveSettings.scope === "first") return
        return
      }
      const hint = decision.profile === "generic" ? GENERIC : PROFILE_HINTS[decision.profile as Profile]
      const base = effectiveSettings.qualityGate === "pass" ? BASE_ALWAYS : BASE_GATE
      const behaviorText = decision.behavior === "preview" ? PREVIEW : (effectiveSettings.qualityGate === "pass" ? AUTO_ALWAYS : AUTO_GATE)
      event.system.push({ text: `${base}\n${hint}\n${behaviorText}\n${buildLifecycle(effectiveSettings)}\n${formatDecision(decision, settings, stored)}` })
    })

  },
})
