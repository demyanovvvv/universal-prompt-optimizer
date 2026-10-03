import type { TaskType } from "./types"
import type { PromptAnalysis } from "./prompt-analysis"

export const POLICY_ORDER: TaskType[] = ["security", "review", "migration", "bugfix", "refactor", "implementation", "testing", "research", "planning", "documentation"]

export function taskPolicies(taskTypes: TaskType[], analysis: PromptAnalysis): string[] {
  const types = new Set(taskTypes)
  return POLICY_ORDER.flatMap(type => {
    if (!types.has(type)) return []
    if (type === "security" || type === "review") return ["Report findings first with location, evidence, impact, and confidence.", analysis.readOnly ? "Do not modify files or perform remediation." : "Do not modify files unless remediation is explicitly requested."]
    if (type === "bugfix") return analysis.readOnly ? ["Use read-only inspection and explain the observed cause or proposed fix without changing files."] : ["Identify the observable failure and root cause before changing code.", "Keep the fix in scope and address regressions caused by the change."]
    if (type === "refactor") return ["Preserve public behavior and contracts; update affected references and verify the result."]
    if (type === "migration") return ["Account for compatibility, data or schema impact, recovery considerations, and proportionate validation."]
    if (type === "implementation") return ["Implement the smallest coherent change that satisfies the requested outcome."]
    if (type === "testing") return ["Keep test changes focused on the requested behavior and preserve meaningful coverage."]
    if (type === "research" || type === "planning") return ["Use bounded investigation, distinguish evidence from assumptions, and stop when the requested deliverable is supported."]
    if (type === "documentation") return ["Preserve the requested audience, source of truth, exact commands and examples, and avoid unrelated rewrites."]
    return []
  })
}