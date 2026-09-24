import type { Behavior, QualityGate, Scope, UnsupportedModel } from "./types"

export const CONFIG_SCHEMA_VERSION = 1 as const
export const DEFAULT_SETTINGS = {
  behavior: "auto",
  scope: "all",
  qualityGate: "adaptive",
  unsupportedModel: "skip",
} as const satisfies {
  behavior: Behavior
  scope: Scope
  qualityGate: QualityGate
  unsupportedModel: UnsupportedModel
}

export function normalizeQualityGate(value: unknown): QualityGate | undefined {
  if (value === "pass" || value === "light" || value === "full" || value === "adaptive") return value
  if (typeof value === "boolean") return value ? "adaptive" : "pass"
  return undefined
}

export function hasInvalidManagedFields(value: Record<string, unknown> | undefined): boolean {
  if (!value) return false
  return (
    ("schemaVersion" in value && (typeof value.schemaVersion !== "number" || value.schemaVersion !== CONFIG_SCHEMA_VERSION))
    || ("behavior" in value && (typeof value.behavior !== "string" || !["auto", "preview", "off"].includes(value.behavior)))
    || ("scope" in value && (typeof value.scope !== "string" || !["first", "all"].includes(value.scope)))
    || ("qualityGate" in value && normalizeQualityGate(value.qualityGate) === undefined)
    || ("unsupportedModel" in value && (typeof value.unsupportedModel !== "string" || !["skip", "generic"].includes(value.unsupportedModel)))
    || ("mode" in value && (typeof value.mode !== "string" || !["first", "all", "off"].includes(value.mode)))
  )
}
