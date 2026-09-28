export type Behavior = "auto" | "preview" | "off"
export type Scope = "first" | "all"
export type QualityGate = "pass" | "light" | "full" | "adaptive"
export type LegacyMode = "first" | "all" | "off"
export type UnsupportedModel = "skip" | "generic"

export type Profile = import("./model-registry").Profile


export type Settings = {
  behavior: Behavior
  scope: Scope
  qualityGate: QualityGate
  unsupportedModel: UnsupportedModel
}

export type SessionOverride = Partial<Settings> & {
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
