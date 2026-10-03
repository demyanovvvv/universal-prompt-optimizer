import type { TaskType } from "./types"
import { analyzeTask } from "./task-classifier"
import { assessRisk } from "./risk-analysis"

export type PromptSignal = "scope" | "constraints" | "validation" | "deliverable"

export type PromptAnalysis = {
  primaryTask: TaskType
  taskTypes: TaskType[]
  hasScope: boolean
  hasConstraints: boolean
  hasValidation: boolean
  hasDeliverable: boolean
  exactLiterals: string[]
  readOnly: boolean
  consequential: boolean
  missingSignals: PromptSignal[]
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
  const risk = assessRisk(normalized)
  const hasScope = exactLiterals.length > 0 || /\b(?:in|from|under|within|across|file|files|module|repo|repository)\b|папк|файл|проект/i.test(normalized)
  const hasConstraints = /\b(?:only|must|keep|preserve|without|don't|do not|avoid|exactly)\b|только|сохрани|сохран|без|не измен|не добав/i.test(normalized)
  const hasValidation = /\b(?:test|tests|testing|verify|validate|check|coverage|assert)\b|проверь|тест|провер/i.test(normalized)
  const hasDeliverable = /\b(?:report|document|explain|output|return|provide|show)\b|отч[её]т|документ|объясни|покажи|предложи/i.test(normalized)
  const missingSignals: PromptSignal[] = [
    ...(!hasScope ? ["scope" as const] : []),
    ...(!hasConstraints ? ["constraints" as const] : []),
    ...(!hasValidation ? ["validation" as const] : []),
    ...(!hasDeliverable ? ["deliverable" as const] : []),
  ]
  const task = analyzeTask(normalized)
  return { primaryTask: task.primaryType, taskTypes: task.types, hasScope, hasConstraints, hasValidation, hasDeliverable, exactLiterals, readOnly, consequential: risk.level === "consequential" && !readOnly, missingSignals }
}