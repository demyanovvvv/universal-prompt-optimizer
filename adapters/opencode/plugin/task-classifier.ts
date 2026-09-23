import type { TaskType } from "./types"
export type { TaskType } from "./types"

export type TaskClassification = {
  type: TaskType
  confidence: "high" | "medium" | "low"
  risk?: "none" | "consequential"
  executionIntent?: "execute" | "plan" | "review" | "explain"
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

const consequentialPattern = /(?:\b(delete|remove|drop|destroy|erase|overwrite|reset|revoke|deploy|publish)\w*\b|\b(?:rotate|change)\s+(?:the\s+)?credentials?\b|\b(?:apply|run|execute)\b[^.!?\n]{0,80}\b(?:production|prod|live|external)\b|\b(?:production|prod|live)\b[^.!?\n]{0,80}\b(?:migrat\w*|schema\w*|delete|remove|drop|overwrite)\b|удал\w*|уничтож\w*|продакшн\w*|боев\w*|внешн\w*|отозв\w*)/i
const planOnlyPattern = /(?:\bplan\s+only\b|\bonly\s+(?:plan|review|analy[sz]e|explain)\b|\b(?:do\s+not|don't|never)\s+(?:modify|change|edit|implement|run|execute)\b|только\s+план|не\s+(?:меняй|изменяй|редактируй|выполняй|запускай))/i
const explainPattern = /\b(?:explain|describe|what\s+is|how\s+does)\b|объясни|расскажи/i

export function classifyTask(prompt: string): TaskClassification {
  const matches = rules.filter(([, pattern]) => pattern.test(prompt))
  const classification: TaskClassification = !matches.length
    ? { type: "unknown", confidence: "low" }
    : {
    type: matches[0][0],
    confidence: matches.length === 1 ? "high" : "medium",
    }
  if (consequentialPattern.test(prompt) && !planOnlyPattern.test(prompt)) classification.risk = "consequential"
  if (planOnlyPattern.test(prompt)) classification.executionIntent = "plan"
  else if (explainPattern.test(prompt) && !matches.some(([type]) => ["implementation", "bugfix", "refactor", "migration"].includes(type))) classification.executionIntent = "explain"
  return classification
}
