import type { QualityGate, TaskType } from "./types"
import { classifyTask } from "./task-classifier"

export type GateSignals = {
  prompt: string
  taskType?: TaskType
  risk?: "none" | "consequential"
  executionIntent?: "execute" | "plan" | "review" | "explain"
}

export function chooseQualityGate(configured: QualityGate, signals: GateSignals): Exclude<QualityGate, "adaptive"> {
  if (configured !== "adaptive") return configured
  const inferred = classifyTask(signals.prompt)
  const risk = signals.risk ?? inferred.risk
  const taskType = signals.taskType ?? inferred.type
  const executionIntent = signals.executionIntent ?? inferred.executionIntent
  if (risk === "consequential") return "full"
  if (executionIntent === "plan" || executionIntent === "explain") return "light"
  if (taskType === "security" || taskType === "migration") return "full"
  if (taskType === "review" || taskType === "research" || taskType === "planning") return "light"
  const prompt = signals.prompt.trim()
  if (taskType === "implementation" || taskType === "bugfix" || taskType === "refactor") {
    if (/\b(?:test|tests|testing|verify|validate|check|passing|pass)\b|тест\w*|провер\w*/i.test(prompt)) return "light"
  }
  if (prompt.length < 80 && !/[?]$/.test(prompt) && !/\b(maybe|somehow|better|improve|etc)\b/i.test(prompt)) return "pass"
  if (/\b(all|every|entire|across|multiple|architecture|integration|production)\b/i.test(prompt) || prompt.length > 280) return "full"
  return "light"
}
