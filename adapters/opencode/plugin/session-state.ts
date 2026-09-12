import { createHash } from "node:crypto"
import type { SessionMetrics, SessionOverride, SessionState } from "./types"

export const STATE_TTL_MS = 30 * 24 * 60 * 60 * 1000

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
    override: normalizeOverride(input.override),
    metrics: normalizeMetrics(input.metrics),
    lastProcessedEventId: typeof input.lastProcessedEventId === "string" ? input.lastProcessedEventId.slice(0, 128) : undefined,
    lastPromptHash: typeof input.lastPromptHash === "string" ? input.lastPromptHash.slice(0, 64) : undefined,
    lastDecision: normalizeDecision(input.lastDecision),
  }
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
  return {
    processed: number("processed"), optimized: number("optimized"), skipped: number("skipped"), previewed: number("previewed"), genericFallback: number("genericFallback"), pass: number("pass"), light: number("light"), full: number("full"),
    lastProfile: typeof input.lastProfile === "string" ? input.lastProfile as SessionMetrics["lastProfile"] : undefined,
    lastGate: typeof input.lastGate === "string" ? input.lastGate as SessionMetrics["lastGate"] : undefined,
    lastAction: typeof input.lastAction === "string" ? input.lastAction as SessionMetrics["lastAction"] : undefined,
  }
}

export function emptyMetrics(): SessionMetrics {
  return { processed: 0, optimized: 0, skipped: 0, previewed: 0, genericFallback: 0, pass: 0, light: 0, full: 0 }
}

export function isDuplicate(state: SessionState | undefined, eventId: string | undefined, prompt: string | undefined): boolean {
  if (!state) return false
  if (eventId && state.lastProcessedEventId === eventId) return true
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
