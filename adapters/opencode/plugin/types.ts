export type Behavior = "auto" | "preview" | "off"
export type Scope = "first" | "all"
export type QualityGate = "pass" | "light" | "full" | "adaptive"
export type LegacyMode = "first" | "all" | "off"
export type UnsupportedModel = "skip" | "generic"

export type Profile =
  | "astra" | "sol" | "terra" | "luna" | "gpt-5.6-sol" | "gpt-5.6-luna"
  | "glm-5.2" | "glm-5.3" | "glm-5.3-flash"
  | "deepseek-v4-flash" | "deepseek-v4-pro"
  | "claude-fable-5.1" | "claude-fable-5" | "claude-opus-5.5" | "claude-opus-5" | "claude-opus-4.8" | "claude-sonnet-5"
  | "kimi-k3" | "muse-spark-1.3" | "hy4-preview" | "qwen3.8-max" | "gemini-3.8-flash" | "grok-4.6"


export type Settings = {
  behavior: Behavior
  scope: Scope
  qualityGate: QualityGate
  unsupportedModel: UnsupportedModel
}

export type SessionOverride = Partial<Pick<Settings, "behavior" | "scope" | "qualityGate">> & {
  profile?: Profile | "auto" | "generic"
}

export type SessionMetrics = {
  processed: number
  optimized: number
  skipped: number
  previewed: number
  genericFallback: number
  pass: number
  light: number
  full: number
  lastProfile?: Profile | "generic"
  lastGate?: Exclude<QualityGate, "adaptive">
  lastAction?: "apply" | "preview" | "skip"
}

export type SessionState = {
  userPromptCount: number
  candidateUserPromptCount?: number
  active: boolean
  lastSeenAt?: number
  override?: SessionOverride
  lastModel?: ModelIdentity
  lastResolution?: ModelResolution
  lastTaskType?: TaskType
  metrics?: SessionMetrics
  lastProcessedEventId?: string
  lastPromptHash?: string
  pendingPromptHash?: string
  lastDecision?: DecisionSummary
}

export type DecisionSummary = {
  action: "apply" | "preview" | "skip"
  profile: Profile | "generic" | "none"
  gate?: Exclude<QualityGate, "adaptive">
  reason: string
  warning?: string
}

export type ConfigSource = "default" | "global" | "project" | "environment" | "session"

export type ResolvedSettings = Settings & {
  sources: {
    behavior: ConfigSource
    scope: ConfigSource
    qualityGate: ConfigSource
    unsupportedModel: ConfigSource
  }
  invalidConfig: boolean
}

export type ModelIdentity = {
  providerID: string
  modelID: string
}

export type ModelResolution = {
  profile?: Profile
  confidence: "high" | "low"
  source: "exact-id" | "pattern" | "unsupported"
  modelID: string
  matchedAlias?: string
}

export type DecisionInput = {
  settings: Settings
  scopeEligible: boolean
  model: ModelIdentity
  profile?: Profile
  sessionOverride?: SessionOverride
  duplicate?: boolean
  taskType?: TaskType
  risk?: "none" | "consequential"
  executionIntent?: "execute" | "plan" | "review" | "explain"
}

export type TaskType = "implementation" | "bugfix" | "refactor" | "review" | "research" | "documentation" | "testing" | "planning" | "security" | "migration" | "unknown"

export type OptimizationDecision = DecisionSummary & {
  behavior: Behavior
  scope: Scope
  qualityGate: QualityGate
  taskType: TaskType
  profileConfidence: "high" | "low"
}

export const PROFILE_IDS = [
  "astra", "sol", "terra", "luna", "gpt-5.6-sol", "gpt-5.6-luna",
  "glm-5.2", "glm-5.3", "glm-5.3-flash",
  "deepseek-v4-flash", "deepseek-v4-pro",
  "claude-fable-5.1", "claude-fable-5", "claude-opus-5.5", "claude-opus-5", "claude-opus-4.8", "claude-sonnet-5",
  "kimi-k3", "muse-spark-1.3", "hy4-preview", "qwen3.8-max", "gemini-3.8-flash", "grok-4.6",
] as const
