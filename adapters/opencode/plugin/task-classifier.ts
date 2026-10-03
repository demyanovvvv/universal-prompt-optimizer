import type { TaskType } from "./types"
import { assessRisk } from "./risk-analysis"
export type { TaskType } from "./types"

export type TaskClassification = {
  type: TaskType
  confidence: "high" | "medium" | "low"
  risk?: "none" | "consequential"
  executionIntent?: "execute" | "plan" | "review" | "explain"
}

export type TaskAnalysis = TaskClassification & {
  types: TaskType[]
  primaryType: TaskType
}

const rules: Array<[TaskType, RegExp]> = [
  ["migration", /\b(migrat\w*|upgrade\w*|downgrad\w*|schema\w*|backfill\w*)\b|миграци\w*|схем\w*/i],
  ["security", /\b(security|vulnerab\w*|secret\w*|credential\w*|permission\w*|exploit\w*|threat\w*)\b|безопасн\w*|секрет\w*|учетн\w*/i],
  ["review", /\b(review|audit|inspect|analy[sz]e|find bugs|code review|pr)\b|проанализир\w*|анализ\w*|аудит\w*|проверь\w*|оцени\w*/i],
  ["bugfix", /\b(fix|bug|error|failure|broken|regression|crash|doesn't work|not working)\b|исправ\w*|ошиб\w*|сбо\w*/i],
  ["refactor", /\b(refactor|rename|reorganize|re-?organize|extract|cleanup|clean up)\b|рефактор\w*|улучш\w*/i],
  ["testing", /\b(test|tests|testing|coverage|assertion|fixture|benchmark)\b|тест\w*|провер\w*/i],
  ["documentation", /\b(document|docs|readme|changelog|guide|explain)\b|документ\w*|описан\w*|объясн\w*/i],
  ["research", /\b(research|compare|investigate|explore|look into|find out)\b|исследу\w*|изучи\w*|сравни\w*/i],
  ["planning", /\b(plan|roadmap|design|propose|architecture)\b|предлож\w*|план\w*|архитектур\w*/i],
  ["implementation", /\b(add|implement|build|create|develop|support|enable)\b/i],
]

const planOnlyPattern = /(?:\bplan\s+only\b|\bonly\s+(?:plan|review|analy[sz]e|explain)\b|\b(?:do\s+not|don't|never)\s+(?:modify|change|edit|implement|run|execute)\b|только\s+план|не\s+(?:меняй|изменяй|редактируй|выполняй|запускай))/i
const explainPattern = /\b(?:explain|describe|what\s+is|how\s+does)\b|объясни|расскажи/i

export function analyzeTask(prompt: string): TaskAnalysis {
  const matches = rules.filter(([, pattern]) => pattern.test(prompt))
  const types = matches.map(([type]) => type)
  const primaryType = types[0] ?? "unknown"
  const classification: TaskClassification = !matches.length
    ? { type: "unknown", confidence: "low" }
    : { type: primaryType, confidence: types.length === 1 || types.length >= 5 ? "high" : "medium" }
  const planOnly = planOnlyPattern.test(prompt)
  if (assessRisk(prompt).level === "consequential" && !planOnly) classification.risk = "consequential"
  if (planOnly) classification.executionIntent = "plan"
  else if (explainPattern.test(prompt) && !types.some(type => ["implementation", "bugfix", "refactor", "migration"].includes(type))) classification.executionIntent = "explain"
  else classification.executionIntent = "execute"
  return { ...classification, types, primaryType }
}

export function classifyTask(prompt: string): TaskClassification {
  const matches = rules.filter(([, pattern]) => pattern.test(prompt))
  const classification: TaskClassification = !matches.length
    ? { type: "unknown", confidence: "low" }
    : {
    type: matches[0][0],
    confidence: matches.length === 1 ? "high" : "medium",
    }
  if (assessRisk(prompt).level === "consequential" && !planOnlyPattern.test(prompt)) classification.risk = "consequential"
  if (planOnlyPattern.test(prompt)) classification.executionIntent = "plan"
  else if (explainPattern.test(prompt) && !matches.some(([type]) => ["implementation", "bugfix", "refactor", "migration"].includes(type))) classification.executionIntent = "explain"
  return classification
}
