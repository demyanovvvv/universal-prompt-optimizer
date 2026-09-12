import type { TaskType } from "./types"
export type { TaskType } from "./types"

export type TaskClassification = {
  type: TaskType
  confidence: "high" | "medium" | "low"
}

const rules: Array<[TaskType, RegExp]> = [
  ["security", /\b(security|vulnerab|secret|credential|auth|oauth|permission|exploit|threat)\b/i],
  ["migration", /\b(migrat|upgrade|downgrad|schema|backfill)\b/i],
  ["review", /\b(review|audit|inspect|analy[sz]e|find bugs|code review|pr)\b/i],
  ["bugfix", /\b(fix|bug|error|failure|broken|regression|crash|doesn't work|not working)\b/i],
  ["refactor", /\b(refactor|rename|reorganize|re-?organize|extract|cleanup|clean up)\b/i],
  ["testing", /\b(test|tests|testing|coverage|assertion|fixture|benchmark)\b/i],
  ["documentation", /\b(document|docs|readme|changelog|guide|explain)\b/i],
  ["research", /\b(research|compare|investigate|explore|look into|find out)\b/i],
  ["planning", /\b(plan|roadmap|design|propose|architecture)\b/i],
  ["implementation", /\b(add|implement|build|create|develop|support|enable)\b/i],
]

export function classifyTask(prompt: string): TaskClassification {
  const matches = rules.filter(([, pattern]) => pattern.test(prompt))
  if (!matches.length) return { type: "unknown", confidence: "low" }
  return {
    type: matches[0][0],
    confidence: matches.length === 1 ? "high" : "medium",
  }
}
