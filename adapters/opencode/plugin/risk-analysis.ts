import type { TaskType } from "./types"

export type RiskCategory = "destructive" | "production" | "external" | "credentials" | "irreversible" | "scope-expansion"
export type RiskLevel = "none" | "review" | "consequential"
export type RiskAssessment = { level: RiskLevel; categories: RiskCategory[]; requiresApproval: boolean; evidence: string[] }

const categoryPatterns: Array<[RiskCategory, RegExp]> = [
  ["destructive", /\b(?:delete|remove|drop|destroy|erase|overwrite|reset|revoke)\w*\b|удал\w*|уничтож\w*|отозв\w*/i],
  ["production", /\b(?:production|prod|live)\b|продакшн\w*|боев\w*/i],
  ["external", /\b(?:external|publish|deploy|send|upload)\w*\b|внешн\w*|опубликов\w*|разверн\w*/i],
  ["credentials", /\b(?:rotate|change|expose|print|commit|store|send|share)\w*\s+(?:the\s+)?(?:credential|secret|password|token|api key)\w*\b|(?:секрет\w*|парол\w*|учетн\w*)\s+(?:показыва\w*|печата\w*|публикува\w*|сохраня\w*)/i],
  ["irreversible", /\b(?:irreversible|permanent|cannot be undone)\b|необратим\w*|навсегда/i],
  ["scope-expansion", /\b(?:entire|every|all|across the organization|unrelated)\b|весь|всю|все|организац\w*/i],
]
function isNegated(prompt: string, _match: string, index: number): boolean {
  const prefix = prompt.slice(Math.max(0, index - 32), index)
  return /(?:\b(?:do not|don't|never|without|no)\s*)$|(?:не\s*)$/i.test(prefix)
}

export function assessRisk(prompt: string, _taskType?: TaskType): RiskAssessment {
  const categories = new Set<RiskCategory>()
  const evidence = new Set<string>()
  for (const [category, pattern] of categoryPatterns) {
    const match = pattern.exec(prompt)
    if (!match || isNegated(prompt, match[0], match.index)) continue
    categories.add(category)
    evidence.add(match[0])
  }
  const ordered = categoryPatterns.map(([category]) => category).filter(category => categories.has(category) && (category !== "scope-expansion" || /across the organization|unrelated|организац\w*/i.test(prompt)))
  const level: RiskLevel = ordered.includes("destructive") || ordered.includes("production") || ordered.includes("external") || ordered.includes("credentials") || ordered.includes("irreversible") ? "consequential" : ordered.length ? "review" : "none"
  return { level, categories: ordered, requiresApproval: level === "consequential", evidence: [...evidence] }
}