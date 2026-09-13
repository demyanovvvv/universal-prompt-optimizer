import { chooseQualityGate } from "./quality-gate"
import type { DecisionInput, OptimizationDecision, Profile, TaskType } from "./types"

export function decide(input: DecisionInput, prompt = ""): OptimizationDecision {
  const settings = input.settings
  const behavior = input.sessionOverride?.behavior ?? settings.behavior
  const scope = input.sessionOverride?.scope ?? settings.scope
  const qualityGate = input.sessionOverride?.qualityGate ?? settings.qualityGate
  const profile = input.sessionOverride?.profile === "generic"
    ? "generic"
    : input.sessionOverride?.profile && input.sessionOverride.profile !== "auto"
      ? input.sessionOverride.profile
      : input.profile ?? (settings.unsupportedModel === "generic" ? "generic" : "none")
  const taskType = input.taskType ?? "unknown"
  const gate = chooseQualityGate(qualityGate, {
    prompt,
    taskType: taskType as TaskType,
    risk: input.risk,
    executionIntent: input.executionIntent,
  })
  if (input.duplicate) {
    return { action: "skip", behavior, scope, qualityGate, taskType, profile: "none", profileConfidence: "low", reason: "duplicate event" }
  }
  if (behavior === "off") {
    return { action: "skip", behavior, scope, qualityGate, taskType, profile: "none", profileConfidence: "low", reason: "optimizer disabled" }
  }
  if (!input.scopeEligible) {
    return { action: "skip", behavior, scope, qualityGate, taskType, profile: "none", profileConfidence: "low", reason: `scope=${scope} is not eligible for this user-turn` }
  }
  if (profile === "none") {
    return { action: "skip", behavior, scope, qualityGate, taskType, profile: "none", profileConfidence: "low", reason: "model is not in the registry" }
  }
  return {
    action: behavior === "preview" ? "preview" : "apply",
    behavior,
    scope,
    qualityGate,
    taskType,
    profile: profile as Profile | "generic",
    profileConfidence: profile === "generic" ? "low" : "high",
    gate,
    reason: gate === "pass" ? "request is already precise" : `${gate} quality gate selected for this task`,
    warning: profile === "generic" ? "model identity is not in the registry; using neutral guidance" : undefined,
  }
}
