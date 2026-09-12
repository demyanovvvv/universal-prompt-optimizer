import type { QualityGate, TaskType } from "./types"

export type GateSignals = {
  prompt: string
  taskType?: TaskType
  risk?: "none" | "consequential"
}

export function chooseQualityGate(configured: QualityGate, signals: GateSignals): Exclude<QualityGate, "adaptive"> {
  if (configured !== "adaptive") return configured
  if (signals.risk === "consequential") return "full"
  if (signals.taskType === "security" || signals.taskType === "migration") return "full"
  if (signals.taskType === "review" || signals.taskType === "research" || signals.taskType === "planning") return "light"
  const prompt = signals.prompt.trim()
  if (prompt.length < 80 && !/[?]$/.test(prompt) && !/\b(maybe|somehow|better|improve|etc)\b/i.test(prompt)) return "pass"
  if (/\b(all|every|entire|across|multiple|architecture|integration|production)\b/i.test(prompt) || prompt.length > 280) return "full"
  return "light"
}
