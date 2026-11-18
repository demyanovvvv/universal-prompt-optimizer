// Universal Prompt Optimizer v5.17 - DeepSeek Harness (Cordis) runtime adapter.
//
// Registers one native system-prompt section. On each assembly it reads the shared
// prompt-optimizer configuration, resolves the active model route from the assembly's
// model-selection snapshot, and emits the installed canonical profile's heading and
// actionable guidance when that route has an exact registry alias (provenance lines and
// source/runtime footers are dropped as non-guidance). It never replaces the whole
// prompt, never mutates host state, and contributes nothing when configuration is
// invalid, behavior is OFF, or an unsupported route must be skipped.

import { existsSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

export const name = "universal-prompt-optimizer"
export const inject = ["systemPrompt", "agents", "workingDirectory"]

const VERSION = "5.17"
const SECTION_NAME = "universal-prompt-optimizer"
const SECTION_ORDER = 10300

const BEHAVIORS = new Set(["auto", "preview", "off"])
const SCOPES = new Set(["first", "all"])
const QUALITY_GATES = new Set(["pass", "light", "full", "adaptive"])
const UNSUPPORTED_MODELS = new Set(["skip", "generic"])
const LEGACY_MODES = new Set(["first", "all", "off"])
const SCHEMA_VERSION = 1

// Resolved through `homedir()` at each assembly. The installed plugin is host-global,
// so the shared global config follows the current user rather than a captured path.
function sharedGlobalConfigPath() {
  return join(homedir(), ".config", "prompt-optimizer", "config.json")
}

// Each installed native bundle carries the canonical skill alongside its runtime.
// The separate `<root>/.dsh/skills` copy remains available for manual discovery.
const SKILL_ROOT = fileURLToPath(new URL("./skills/prompt-optimizer", import.meta.url))
const REGISTRY_PATH = join(SKILL_ROOT, "references", "model-registry.json")
const PROFILE_ROOT = join(SKILL_ROOT, "references")

// Shared optimization invariants plus the explicit quality-gate mode. Deliberately
// model-neutral: model guidance arrives only as the selected canonical profile text.
const SHARED_INVARIANTS =
  "Prompt Optimizer v" + VERSION + ": model-aware preflight for this request.\n"
  + "Preserve the user's intent, exact literals, hard constraints, project rules, requested output, required verification and approval boundaries; do not invent requirements. "
  + "Resolve shorthand from relevant context. Keep the brief as lean as the task and model permit.\n"
  + "Native Reasoning First: never request hidden chain-of-thought and never add generic 'think step by step', 'think harder' or 'show reasoning' scaffolding. "
  + "Thinking, sampling, cache and tool history stay host-controlled.\n"
  + "User, host and repository instructions outrank this preflight."

const MODE_AUTO = "Execution mode AUTO: apply only the selected quality gate below; silently shape the request and continue authorized work in this turn."
const MODE_PREVIEW = "Execution mode PREVIEW: optimize for the gate below, then stop for approval before executing."
const GATE_PASS =
  "Quality gate PASS: normalize the request into the leanest model-appropriate execution brief without adding requirements or structure."
const GATE_LIGHT =
  "Quality gate LIGHT: add only a missing high-value scope boundary, hard constraint, done criterion, approval boundary or exact output shape."
const GATE_FULL = "Quality gate FULL: build a concise execution brief from only the task-relevant context."
const GATE_ADAPTIVE = "Quality gate ADAPTIVE: select PASS/LIGHT/FULL from the request before acting."
const GATE_AUTO_TAIL = "Then execute in this same turn."
const PREVIEW_TEXT =
  "Before any mutating or external action, form the exact optimized execution prompt for this request. "
  + "Read-only context resolution may happen first; do not start mutation-capable work before approval. "
  + "Present that exact prompt for explicit user confirmation, then stop and wait for the confirmation. "
  + "Treat an edited or customized prompt as the source of truth and execute that text. Never treat missing confirmation as approval."
const GENERIC_FALLBACK =
  "Neutral fallback profile: use only model- and provider-neutral shaping. Do not assume provider-specific reasoning, sampling, tool-history or cache behavior."

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

// --- canonical registry (read once) -----------------------------------------

let registryState

function loadRegistry() {
  if (registryState !== undefined) return registryState
  registryState = null
  let parsed
  try {
    parsed = JSON.parse(readFileSync(REGISTRY_PATH, "utf8"))
  } catch {
    return registryState
  }
  if (!isPlainObject(parsed) || !Array.isArray(parsed.profiles)) return registryState
  const aliases = new Map()
  const files = new Map()
  for (const profile of parsed.profiles) {
    if (!isPlainObject(profile) || typeof profile.id !== "string" || !profile.id) continue
    if (typeof profile.file === "string" && profile.file) files.set(profile.id, profile.file)
    if (!Array.isArray(profile.aliases)) continue
    for (const alias of profile.aliases) {
      if (typeof alias !== "string" || !alias) continue
      const key = normalizeModelID(alias)
      if (key) aliases.set(key, profile.id)
    }
  }
  registryState = { aliases, files }
  return registryState
}

// Exact alias matching only: lowercase, underscores to hyphens, last path segment,
// and the supported `-latest` fallback. No fuzzy, family or near-version matching.
function normalizeModelID(value) {
  if (typeof value !== "string") return ""
  const trimmed = value.trim().toLowerCase().replace(/_/g, "-")
  if (!trimmed) return ""
  const segments = trimmed.split("/")
  return segments[segments.length - 1]
}

function resolveProfile(model) {
  const state = loadRegistry()
  if (state === null) return undefined
  const id = normalizeModelID(model)
  if (!id) return undefined
  const direct = state.aliases.get(id)
  if (direct !== undefined) return direct
  if (id.endsWith("-latest")) return state.aliases.get(id.slice(0, -"-latest".length))
  return undefined
}

// The canonical profile document is the model guidance. Only its heading and its
// actionable body paragraphs reach the prompt: the provenance line and the official
// source / runtime footers are provenance metadata, not shaping guidance.
function profileText(state, id) {
  const file = state.files.get(id)
  if (file === undefined) return undefined
  let raw
  try {
    raw = readFileSync(join(PROFILE_ROOT, file), "utf8")
  } catch {
    return undefined
  }
  const guidance = actionGuidance(raw)
  return guidance ? { text: guidance, file } : undefined
}

const PROVENANCE_LINE = /^\*\*Provenance:\*\*/
const FOOTER_LINE = /^(?:Official sources?:|Runtime(?:\/API settings)?:|Shared guidance)/i

function actionGuidance(raw) {
  const kept = []
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (PROVENANCE_LINE.test(trimmed)) continue
    if (FOOTER_LINE.test(trimmed)) break
    if (!trimmed) continue
    kept.push(trimmed.startsWith("#") ? trimmed : line.replace(/\s+$/, ""))
  }
  return kept.join("\n").trim()
}

// --- configuration ----------------------------------------------------------

function normalizeQualityGate(value) {
  if (typeof value === "boolean") return value ? "adaptive" : "pass"
  return typeof value === "string" && QUALITY_GATES.has(value) ? value : undefined
}

// Mirrors the pure config_contract field validation: unrelated fields are preserved,
// while any managed field that violates the public schema invalidates its source.
function hasInvalidManagedFields(value) {
  return (
    ("schemaVersion" in value && (typeof value.schemaVersion !== "number" || value.schemaVersion !== SCHEMA_VERSION))
    || ("behavior" in value && !(typeof value.behavior === "string" && BEHAVIORS.has(value.behavior)))
    || ("scope" in value && !(typeof value.scope === "string" && SCOPES.has(value.scope)))
    || ("qualityGate" in value && normalizeQualityGate(value.qualityGate) === undefined)
    || ("unsupportedModel" in value && !(typeof value.unsupportedModel === "string" && UNSUPPORTED_MODELS.has(value.unsupportedModel)))
    || ("mode" in value && !(typeof value.mode === "string" && LEGACY_MODES.has(value.mode)))
  )
}

function readSource(path) {
  if (!existsSync(path)) return null
  let parsed
  try {
    parsed = JSON.parse(readFileSync(path, "utf8"))
  } catch {
    return undefined
  }
  if (!isPlainObject(parsed) || hasInvalidManagedFields(parsed)) return undefined
  return parsed
}

// Any malformed source fails closed to OFF; otherwise project values override valid
// global values, and legacy `mode` supplies behavior/scope where the newer key is absent.
function settingsFor(cwd) {
  const global = readSource(sharedGlobalConfigPath())
  const project = readSource(join(cwd, ".prompt-optimizer.json"))
  if (global === undefined || project === undefined) {
    return { behavior: "off", scope: "all", qualityGate: "adaptive", unsupportedModel: "skip" }
  }
  const behavior = project?.behavior ?? global?.behavior
  const scope = project?.scope ?? global?.scope
  const legacy = project?.mode ?? global?.mode
  const qualityGate = normalizeQualityGate(project ? project.qualityGate : undefined)
    ?? normalizeQualityGate(global?.qualityGate)
    ?? "adaptive"
  const unsupportedModel = project?.unsupportedModel ?? global?.unsupportedModel
  return {
    behavior: BEHAVIORS.has(behavior) ? behavior : legacy === "off" ? "off" : "auto",
    scope: SCOPES.has(scope) ? scope : legacy === "first" || legacy === "all" ? legacy : "all",
    qualityGate,
    unsupportedModel: unsupportedModel === "generic" ? "generic" : "skip",
  }
}

// --- section assembly -------------------------------------------------------

const EMPTY = ""

function sectionText(context, activeCwd, activeBoundary) {
  const agent = context === null || typeof context !== "object" ? undefined : context.agent
  const snapshot = context === null || typeof context !== "object" ? undefined : context.modelSelection
  if (!agent) return EMPTY

  // A missing or malformed model-selection snapshot is an unsupported policy: the
  // assembly cannot name a route, so the optimizer never guesses one.
  const unsupportedRoute = !isPlainObject(snapshot) || typeof snapshot.model !== "string"

  // The active directory selects which project config applies. A host read error, a
  // missing value or a non-string result is not a reason to guess another project's
  // directory, so the section fails closed instead of falling back to process.cwd().
  let cwd
  try {
    const value = activeCwd(agent.session)
    if (typeof value !== "string" || !value) return EMPTY
    cwd = value
  } catch {
    return EMPTY
  }

  const settings = settingsFor(cwd)
  if (settings.behavior === "off") return EMPTY

  // `first` scope binds to the session's durable first turn, across every step and
  // retry of that turn. A knowably later turn is skipped; an unreadable boundary is
  // not treated as the first turn.
  if (settings.scope === "first") {
    let turn
    try {
      turn = activeBoundary(agent.session)?.lastTurn
    } catch {
      turn = undefined
    }
    if (turn !== 1) return EMPTY
  }

  // Only the exact model leaf selects a profile; the provider is metadata, never an alias.
  const profile = unsupportedRoute ? undefined : resolveProfile(snapshot.model)
  if (profile === undefined) {
    if (settings.unsupportedModel === "skip") return EMPTY
    return [SHARED_INVARIANTS, scopeLine(settings), ...modeLines(settings), GENERIC_FALLBACK].join("\n\n")
  }

  const selected = profileText(loadRegistry(), profile)
  if (selected === undefined) return EMPTY
  return [
    SHARED_INVARIANTS,
    scopeLine(settings),
    ...modeLines(settings),
    `Selected canonical profile: \`${profile}\` -> references/${selected.file}`,
    selected.text,
  ].join("\n\n")
}

function scopeLine(settings) {
  return `Scope: ${settings.scope}.`
}

// Shaping guidance and execution permission are separate facts: the gate never claims
// the work may proceed, and PREVIEW never hides the selected gate level.
function modeLines(settings) {
  const gate = settings.qualityGate === "pass"
    ? GATE_PASS
    : settings.qualityGate === "light"
      ? GATE_LIGHT
      : settings.qualityGate === "full"
        ? GATE_FULL
        : GATE_ADAPTIVE
  if (settings.behavior === "preview") return [MODE_PREVIEW, gate + " " + PREVIEW_TEXT]
  return [MODE_AUTO, gate + " " + GATE_AUTO_TAIL]
}

export function apply(ctx) {
  // A section text function cannot receive the Cordis context, so the two services
  // the assembly needs are captured once at registration.
  const workingDirectory = ctx.workingDirectory
  const agents = ctx.agents
  const readCwd = session => workingDirectory.get(session)
  const readBoundary = session => agents.turnBoundaryOf(session)
  ctx.systemPrompt.section({
    name: SECTION_NAME,
    order: SECTION_ORDER,
    interpolate: false,
    text: context => sectionText(context, readCwd, readBoundary),
  })
}
