import { existsSync, lstatSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join, resolve } from "node:path"
import type { Settings } from "./types"
import { CONFIG_SCHEMA_VERSION, DEFAULT_SETTINGS, hasInvalidManagedFields } from "./config-contract"

export type ConfigTarget = "global" | "project" | "session"
const managedKeys = ["schemaVersion", "behavior", "scope", "qualityGate", "unsupportedModel"] as const

export function configPathForTarget(projectRoot: string, target: ConfigTarget, home = homedir()): string | undefined {
  if (target === "session") return undefined
  return target === "project"
    ? join(projectRoot, ".opencode", "prompt-optimizer.json")
    : join(home, ".config", "opencode", "prompt-optimizer.json")
}

export function loadManagedConfig(path: string): Record<string, unknown> {
  if (!existsSync(path)) return {}
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
  } catch {
    return {}
  }
}

function assertManagedConfig(value: Record<string, unknown>): void {
  if (hasInvalidManagedFields(value)) throw new Error("Prompt Optimizer configuration contains invalid managed fields")
}

export function rejectSymlinkComponents(path: string): void {
  let current = resolve(path)
  while (true) {
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) throw new Error("Refusing to write through a symlink")
    const parent = dirname(current)
    if (parent === current) return
    current = parent
  }
}

export function updateManagedConfig(path: string, patch: Partial<Settings>): Record<string, unknown> {
  rejectSymlinkComponents(path)
  const current = loadManagedConfig(path)
  if (existsSync(path) && Object.keys(current).length === 0) throw new Error("Prompt Optimizer configuration is invalid")
  const next: Record<string, unknown> = { ...current, schemaVersion: CONFIG_SCHEMA_VERSION, ...patch }
  assertManagedConfig(next)
  const temp = `${path}.tmp-${process.pid}-${Date.now()}`
  try {
    mkdirSync(dirname(path), { recursive: true })
    if (lstatSync(dirname(path)).isSymbolicLink()) throw new Error("Refusing to write through a symlink")
    // Keep the write local to the destination directory so rename is atomic.
    writeFileSync(temp, `${JSON.stringify(next, null, 2)}\n`, { encoding: "utf8", mode: 0o600 })
    renameSync(temp, path)
  } finally {
    try { unlinkSync(temp) } catch { /* already renamed */ }
  }
  return next
}

export function managedSettingsFromConfig(value: Record<string, unknown>): Partial<Settings> {
  return Object.fromEntries(managedKeys.filter(key => key !== "schemaVersion" && key in value).map(key => [key, value[key]])) as Partial<Settings>
}

export function loadSessionSettings(sessionID: string, home = homedir()): Partial<Settings> {
  const value = loadManagedConfig(join(home, ".config", "opencode", "prompt-optimizer-sessions", `${encodeURIComponent(sessionID)}.json`))
  if (hasInvalidManagedFields(value)) return {}
  return managedSettingsFromConfig(value)
}

export function clearSessionSettings(sessionID: string, home = homedir()): void {
  const path = join(home, ".config", "opencode", "prompt-optimizer-sessions", `${encodeURIComponent(sessionID)}.json`)
  if (!existsSync(path)) return
  rejectSymlinkComponents(path)
  unlinkSync(path)
}

export { DEFAULT_SETTINGS }
