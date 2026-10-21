import { createHash } from "node:crypto"
import type { SessionMetrics, SessionOverride, SessionState } from "./types"
import { PROFILE_IDS } from "./model-registry"

export const STATE_TTL_MS = 30 * 24 * 60 * 60 * 1000
export const MAX_SESSIONS = 200

export function hashPrompt(prompt: string): string {
  return createHash("sha256").update(prompt).digest("hex").slice(0, 16)
}

export function normalizeState(value: unknown): SessionState | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  if (typeof input.userPromptCount !== "number" || typeof input.active !== "boolean") return undefined
  return {
    userPromptCount: Math.max(0, Math.floor(input.userPromptCount)),
    candidateUserPromptCount: typeof input.candidateUserPromptCount === "number" ? Math.max(0, Math.floor(input.candidateUserPromptCount)) : undefined,
    active: input.active,
    lastSeenAt: typeof input.lastSeenAt === "number" ? Math.max(0, input.lastSeenAt) : undefined,
    override: normalizeOverride(input.override),
    lastModel: normalizeModel(input.lastModel),
    lastResolution: normalizeResolution(input.lastResolution),
    lastTaskType: normalizeTaskType(input.lastTaskType),
    metrics: normalizeMetrics(input.metrics),
    lastProcessedEventId: typeof input.lastProcessedEventId === "string" ? input.lastProcessedEventId.slice(0, 128) : undefined,
    lastPromptHash: typeof input.lastPromptHash === "string" ? input.lastPromptHash.slice(0, 64) : undefined,
    pendingPromptHash: typeof input.pendingPromptHash === "string" ? input.pendingPromptHash.slice(0, 64) : undefined,
    lastDecision: normalizeDecision(input.lastDecision),
  }
}

function normalizeModel(value: unknown): SessionState["lastModel"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  if (typeof input.providerID !== "string" || typeof input.modelID !== "string") return undefined
  return { providerID: input.providerID.slice(0, 128), modelID: input.modelID.slice(0, 128) }
}

function normalizeResolution(value: unknown): SessionState["lastResolution"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  if (input.confidence !== "high" && input.confidence !== "low") return undefined
  if (input.source !== "exact-id" && input.source !== "pattern" && input.source !== "unsupported") return undefined
  if (typeof input.modelID !== "string") return undefined
  const profiles = PROFILE_IDS
  return {
    profile: typeof input.profile === "string" && profiles.includes(input.profile as typeof profiles[number]) ? input.profile as NonNullable<SessionState["lastResolution"]>["profile"] : undefined,
    confidence: input.confidence,
    source: input.source,
    modelID: input.modelID.slice(0, 128),
    matchedAlias: typeof input.matchedAlias === "string" ? input.matchedAlias.slice(0, 128) : undefined,
  }
}

function normalizeTaskType(value: unknown): SessionState["lastTaskType"] {
  const values = ["implementation", "bugfix", "refactor", "review", "research", "documentation", "testing", "planning", "security", "migration", "unknown"] as const
  return typeof value === "string" && values.includes(value as typeof values[number]) ? value as SessionState["lastTaskType"] : undefined
}

function normalizeDecision(value: unknown): SessionState["lastDecision"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  if (input.action !== "apply" && input.action !== "preview" && input.action !== "skip") return undefined
  if (typeof input.profile !== "string" || typeof input.reason !== "string") return undefined
  return {
    action: input.action,
    profile: input.profile as NonNullable<SessionState["lastDecision"]>["profile"],
    gate: input.gate === "pass" || input.gate === "light" || input.gate === "full" ? input.gate : undefined,
    reason: input.reason.slice(0, 240),
    warning: typeof input.warning === "string" ? input.warning.slice(0, 240) : undefined,
  }
}

function normalizeOverride(value: unknown): SessionOverride | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  const output: SessionOverride = {}
  if (input.behavior === "auto" || input.behavior === "preview" || input.behavior === "off") output.behavior = input.behavior
  if (input.scope === "first" || input.scope === "all") output.scope = input.scope
  if (input.qualityGate === "pass" || input.qualityGate === "light" || input.qualityGate === "full" || input.qualityGate === "adaptive") output.qualityGate = input.qualityGate
  if (input.profile === "auto" || input.profile === "generic" || typeof input.profile === "string") output.profile = input.profile as SessionOverride["profile"]
  return Object.keys(output).length ? output : undefined
}

function normalizeMetrics(value: unknown): SessionMetrics | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined
  const input = value as Record<string, unknown>
  const number = (key: string) => typeof input[key] === "number" ? Math.max(0, Math.floor(input[key] as number)) : 0
  const profiles = new Set<string>([...PROFILE_IDS, "generic"])
  return {
    processed: number("processed"), optimized: number("optimized"), skipped: number("skipped"), previewed: number("previewed"), genericFallback: number("genericFallback"), pass: number("pass"), light: number("light"), full: number("full"),
    lastProfile: typeof input.lastProfile === "string" && profiles.has(input.lastProfile) ? input.lastProfile as SessionMetrics["lastProfile"] : undefined,
    lastGate: input.lastGate === "pass" || input.lastGate === "light" || input.lastGate === "full" ? input.lastGate : undefined,
    lastAction: input.lastAction === "apply" || input.lastAction === "preview" || input.lastAction === "skip" ? input.lastAction : undefined,
  }
}

export function emptyMetrics(): SessionMetrics {
  return { processed: 0, optimized: 0, skipped: 0, previewed: 0, genericFallback: 0, pass: 0, light: 0, full: 0 }
}

export function isDuplicate(state: SessionState | undefined, eventId: string | undefined, prompt: string | undefined): boolean {
  if (!state) return false
  if (eventId && state.lastProcessedEventId === eventId) return true
  // The prompt hook reserves the current user turn before the context hook runs.
  // Do not compare that turn with the previous turn's hash, otherwise repeating
  // the same user text is incorrectly discarded as a duplicate.
  if (state.pendingPromptHash) return false
  return Boolean(prompt && state.lastPromptHash === hashPrompt(prompt))
}

export function incrementMetrics(state: SessionState, action: "apply" | "preview" | "skip", profile: string, gate?: "pass" | "light" | "full"): SessionMetrics {
  const metrics = { ...emptyMetrics(), ...(state.metrics ?? {}) }
  metrics.processed++
  if (action === "apply") metrics.optimized++
  if (action === "preview") metrics.previewed++
  if (action === "skip") metrics.skipped++
  if (profile === "generic") metrics.genericFallback++
  if (gate) metrics[gate]++
  metrics.lastProfile = profile as SessionMetrics["lastProfile"]
  metrics.lastGate = gate
  metrics.lastAction = action
  return metrics
}

export function pruneSessions<T extends { state: SessionState }>(sessions: Map<string, T>, now = Date.now()): void {
  const cutoff = now - STATE_TTL_MS
  for (const [key, value] of sessions) {
    if ((value.state.lastSeenAt ?? now) < cutoff) sessions.delete(key)
  }
  if (sessions.size <= MAX_SESSIONS) return
  const ranked = [...sessions.entries()].sort(([, left], [, right]) => (right.state.lastSeenAt ?? 0) - (left.state.lastSeenAt ?? 0))
  for (const [key] of ranked.slice(MAX_SESSIONS)) sessions.delete(key)
}

export function isSessionExpired(state: SessionState, now = Date.now()): boolean {
  return typeof state.lastSeenAt === "number" && state.lastSeenAt < now - STATE_TTL_MS
}
