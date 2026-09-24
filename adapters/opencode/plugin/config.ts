import { existsSync, readFileSync, statSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import type { ConfigSource, QualityGate, ResolvedSettings, Settings } from "./types"
import { DEFAULT_SETTINGS, hasInvalidManagedFields, normalizeQualityGate } from "./config-contract"

export type PluginOptions = Record<string, unknown>

type JsonObject = Record<string, unknown>

export function qualityGateFromEnvironment(value: unknown): QualityGate | undefined {
  if (typeof value !== "string") return undefined
  if (["false", "off", "0"].includes(value.toLowerCase())) return "pass"
  return normalizeQualityGate(value)
}

export function readJson(path: string): JsonObject | undefined {
  if (!existsSync(path)) return undefined
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    return value && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : undefined
  } catch {
    return undefined
  }
}

export function hasInvalidJson(path: string): boolean {
  if (!existsSync(path)) return false
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    return !value || typeof value !== "object" || Array.isArray(value)
  } catch {
    return true
  }
}

export { DEFAULT_SETTINGS, hasInvalidManagedFields, normalizeQualityGate }

export function qualityGateValue(value: unknown): QualityGate | undefined {
  return normalizeQualityGate(value)
}

function applyValue<T>(
  value: unknown,
  current: T,
  source: ConfigSource,
  valid: (value: unknown) => value is T,
): { value: T; source: ConfigSource } {
  return valid(value) ? { value, source } : { value: current, source: "default" }
}

function validBehavior(value: unknown): value is Settings["behavior"] {
  return value === "auto" || value === "preview" || value === "off"
}

function validScope(value: unknown): value is Settings["scope"] {
  return value === "first" || value === "all"
}

function validUnsupportedModel(value: unknown): value is Settings["unsupportedModel"] {
  return value === "skip" || value === "generic"
}

export function resolveSettings(
  projectRoot: string,
  options: PluginOptions | undefined,
  env: NodeJS.ProcessEnv = process.env,
): ResolvedSettings {
  const sharedGlobal = join(homedir(), ".config", "prompt-optimizer", "config.json")
  const globalConfig = join(homedir(), ".config", "opencode", "prompt-optimizer.json")
  const sharedProject = join(projectRoot, ".prompt-optimizer.json")
  const projectConfig = join(projectRoot, ".opencode", "prompt-optimizer.json")
  const paths = [sharedGlobal, globalConfig, sharedProject, projectConfig]
  let invalidConfig = paths.some(path => hasInvalidJson(path) || hasInvalidManagedFields(readJson(path)))
  const values = paths
    .map(path => ({ path, value: readJson(path) }))
    .filter((item): item is { path: string; value: JsonObject } => item.value !== undefined)
  const merged = Object.assign({}, ...values.map(item => item.value), options ?? {})
  if (options && hasInvalidManagedFields(options)) invalidConfig = true
  const legacy = merged.mode === "first" || merged.mode === "all" || merged.mode === "off" ? merged.mode : undefined
  const behaviorEnv = env.PROMPT_OPTIMIZER_BEHAVIOR
  const scopeEnv = env.PROMPT_OPTIMIZER_SCOPE
  const qualityEnv = env.PROMPT_OPTIMIZER_QUALITY_GATE
  const unsupportedEnv = env.PROMPT_OPTIMIZER_UNSUPPORTED_MODEL
  if (
    (behaviorEnv !== undefined && !validBehavior(behaviorEnv))
    || (scopeEnv !== undefined && !validScope(scopeEnv))
    || (qualityEnv !== undefined && qualityGateFromEnvironment(qualityEnv) === undefined)
    || (unsupportedEnv !== undefined && !validUnsupportedModel(unsupportedEnv))
  ) invalidConfig = true
  const highestFileSource: ConfigSource = values.some(item => item.path === projectConfig || item.path === sharedProject) ? "project" : values.some(item => item.path === globalConfig || item.path === sharedGlobal) ? "global" : "default"
  const optionsSource: ConfigSource = options && Object.keys(options).length ? "environment" : highestFileSource
  const behaviorResult = behaviorEnv !== undefined
    ? applyValue(behaviorEnv, DEFAULT_SETTINGS.behavior, "environment", validBehavior)
    : applyValue(merged.behavior ?? (legacy === "off" ? "off" : undefined), DEFAULT_SETTINGS.behavior, optionsSource, validBehavior)
  const scopeResult = scopeEnv !== undefined
    ? applyValue(scopeEnv, DEFAULT_SETTINGS.scope, "environment", validScope)
    : applyValue(merged.scope ?? (legacy === "first" || legacy === "all" ? legacy : undefined), DEFAULT_SETTINGS.scope, optionsSource, validScope)
  const qualityResult = qualityEnv !== undefined
    ? applyValue(qualityGateFromEnvironment(qualityEnv), DEFAULT_SETTINGS.qualityGate, "environment", (value): value is QualityGate => normalizeQualityGate(value) !== undefined)
    : applyValue(normalizeQualityGate(merged.qualityGate), DEFAULT_SETTINGS.qualityGate, optionsSource, (value): value is QualityGate => normalizeQualityGate(value) !== undefined)
  const unsupportedResult = unsupportedEnv !== undefined
    ? applyValue(unsupportedEnv, DEFAULT_SETTINGS.unsupportedModel, "environment", validUnsupportedModel)
    : applyValue(merged.unsupportedModel, DEFAULT_SETTINGS.unsupportedModel, optionsSource, validUnsupportedModel)
  const settings: Settings = {
    behavior: behaviorResult.value,
    scope: scopeResult.value,
    qualityGate: qualityResult.value,
    unsupportedModel: unsupportedResult.value,
  }
  return {
    ...settings,
    behavior: invalidConfig ? "off" : settings.behavior,
    sources: {
      behavior: invalidConfig ? "default" : behaviorResult.source,
      scope: scopeResult.source,
      qualityGate: qualityResult.source,
      unsupportedModel: unsupportedResult.source,
    },
    invalidConfig,
  }
}

export function configPaths(projectRoot: string): string[] {
  return [
    join(homedir(), ".config", "prompt-optimizer", "config.json"),
    join(homedir(), ".config", "opencode", "prompt-optimizer.json"),
    join(projectRoot, ".prompt-optimizer.json"),
    join(projectRoot, ".opencode", "prompt-optimizer.json"),
  ]
}

export function configSourceLabel(source: ConfigSource): string {
  return source === "project" ? "project config" : source === "global" ? "global config" : source
}

export function configMtime(projectRoot: string): number {
  return configPaths(projectRoot).reduce((latest, path) => {
    try { return Math.max(latest, statSync(path).mtimeMs) } catch { return latest }
  }, 0)
}
