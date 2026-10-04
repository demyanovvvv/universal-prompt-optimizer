/** @jsxImportSource @opentui/solid */
import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"
import type { TuiPlugin, TuiPluginModule, TuiSlotPlugin } from "@opencode-ai/plugin/tui"
import { resolveSettings } from "../plugin/config"
import { rejectSymlinkComponents } from "../plugin/tui-config"

export type Status = "enabled" | "preview" | "off" | "generic" | "error"
export function formatStatusChip(input: { status: Status; behavior: Behavior; sessionOverride: boolean }): { label: string; tone: "success" | "info" | "muted" | "warning" | "error"; marker: string } {
  const chips: Record<Status, { label: string; tone: "success" | "info" | "muted" | "warning" | "error" }> = {
    enabled: { label: "● PO AUTO", tone: "success" },
    preview: { label: "◐ PO PREVIEW", tone: "info" },
    off: { label: "○ PO OFF", tone: "muted" },
    generic: { label: "◇ PO GENERIC", tone: "warning" },
    error: { label: "! PO CONFIG", tone: "error" },
  }
  return { ...chips[input.status], marker: input.sessionOverride ? "*" : "" }
}
type Behavior = "auto" | "preview" | "off"
type Scope = "first" | "all"
type QualityGate = "pass" | "light" | "full" | "adaptive"
type UnsupportedModel = "skip" | "generic"
type Target = "global" | "project" | "session"
type Settings = { behavior: Behavior; scope: Scope; qualityGate: QualityGate; unsupportedModel: UnsupportedModel }
type Config = Partial<Settings> & { schemaVersion?: number }

const DEFAULTS: Settings = { behavior: "auto", scope: "all", qualityGate: "adaptive", unsupportedModel: "generic" }
const TARGET_LABELS: Record<Target, string> = { global: "Global", project: "Project", session: "Session" }

function readConfig(path: string): Config {
  if (!existsSync(path)) return {}
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    if (!value || typeof value !== "object" || Array.isArray(value)) return { schemaVersion: -1 }
    const config = value as Config
    if ((config.schemaVersion !== undefined && config.schemaVersion !== 1)
      || (config.behavior !== undefined && !["auto", "preview", "off"].includes(config.behavior))
      || (config.scope !== undefined && !["first", "all"].includes(config.scope))
      || (config.qualityGate !== undefined && !["adaptive", "pass", "light", "full", true, false].includes(config.qualityGate))
      || (config.unsupportedModel !== undefined && !["skip", "generic"].includes(config.unsupportedModel))) return { schemaVersion: -1 }
    return config
  } catch {
    return { schemaVersion: -1 }
  }
}

function paths(api: any): { global: string; project: string } {
  const project = api.state?.path?.directory || process.cwd()
  return {
    global: join(homedir(), ".config", "opencode", "prompt-optimizer.json"),
    project: join(project, ".opencode", "prompt-optimizer.json"),
  }
}

function resolvedSettings(api: any): { settings: Settings; invalid: boolean; source: Target | "default" } {
  const projectRoot = api.state?.path?.directory || process.cwd()
  const resolved = resolveSettings(projectRoot, undefined)
  const source = resolved.sources.behavior === "project" || resolved.sources.scope === "project" || resolved.sources.qualityGate === "project" || resolved.sources.unsupportedModel === "project"
    ? "project"
    : resolved.sources.behavior === "global" || resolved.sources.scope === "global" || resolved.sources.qualityGate === "global" || resolved.sources.unsupportedModel === "global"
      ? "global"
      : "default"
  return { settings: resolved, invalid: resolved.invalidConfig, source }
}

function updateConfig(path: string, patch: Partial<Settings>): void {
  rejectSymlinkComponents(path)
  const current: Record<string, unknown> = readConfig(path)
  if (current.schemaVersion === -1) throw new Error("Invalid Prompt Optimizer configuration")
  const next = { ...current, schemaVersion: 1, ...patch }
  const temp = `${path}.tmp-${process.pid}-${Date.now()}`
  try {
    mkdirSync(dirname(path), { recursive: true })
    writeFileSync(temp, `${JSON.stringify(next, null, 2)}\n`, { encoding: "utf8", mode: 0o600 })
    renameSync(temp, path)
  } finally {
    try { unlinkSync(temp) } catch { /* renamed */ }
  }
}

function sessionPath(sessionID: string): string {
  return join(homedir(), ".config", "opencode", "prompt-optimizer-sessions", `${encodeURIComponent(sessionID)}.json`)
}

function sessionOverride(api: any, sessionID?: string): Partial<Settings> {
  if (!sessionID) return {}
  const config = readConfig(sessionPath(sessionID))
  return config.schemaVersion === -1 ? {} : config
}

function saveSession(sessionID: string, patch: Partial<Settings>): void {
  updateConfig(sessionPath(sessionID), patch)
}

function short(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function sessionDecision(api: any, sessionID?: string): any {
  if (!sessionID) return api.kv?.get?.("prompt-optimizer/decision", undefined)
  return api.kv?.get?.(`prompt-optimizer/decision/${sessionID}`, undefined)
}

function currentSessionID(api: any): string | undefined {
  const route = api.route?.current as { name?: string; params?: Record<string, unknown> } | undefined
  return route?.name === "session" ? String(route.params?.sessionID ?? "") : undefined
}

function statusFromConfig(api: any, sessionID?: string): { status: Status; label: string } {
  const override = sessionOverride(api, sessionID)
  // The server plugin stores session state in server storage, not in the TUI
  // session object. Keep the widget config-level by default; use only explicit
  // TUI KV state when another integration publishes a decision summary.
  const decision = sessionDecision(api, sessionID)
  const resolved = resolvedSettings(api)
  const behavior = override.behavior ?? resolved.settings.behavior
  if (resolved.invalid) return { status: "error", label: "! PO CONFIG" }
  if (behavior === "off") return { status: "off", label: "○ PO OFF" }
  if (behavior === "preview") return { status: "preview", label: "◐ PO PREVIEW" }
  if (decision?.profile === "generic") return { status: "generic", label: "◇ PO GENERIC" }
  return { status: "enabled", label: "● PO AUTO" }
}

function statusDetails(api: any, sessionID?: string): string {
  const current = statusFromConfig(api, sessionID)
  const decision = sessionDecision(api, sessionID)
  const resolved = resolvedSettings(api)
  const override = sessionOverride(api, sessionID)
  const settings = { ...resolved.settings, ...override }
  const lines = [
    "Prompt Optimizer",
    "",
    `Status: ${current.label}`,
    `Mode: ${settings.behavior.toUpperCase()} (${resolved.source})`,
    `Scope: ${settings.scope.toUpperCase()} (${resolved.source})`,
    `Quality gate: ${settings.qualityGate.toUpperCase()} (${resolved.source})`,
    `Unsupported model: ${settings.unsupportedModel.toUpperCase()}`,
  ]
  if (current.status === "preview") lines.push("Preview: advisory (model-guided)")
  if (decision?.model) lines.push(`Model: ${decision.model}`)
  if (decision?.profile) lines.push(`Profile: ${decision.profile}`)
  if (decision?.gate) lines.push(`Gate: ${decision.gate}`)
  if (decision?.reason) lines.push(`Reason: ${decision.reason}`)
  if (resolved.invalid) lines.push("Warning: invalid managed configuration forced safe OFF mode.")
  lines.push("", "Press Esc to close.")
  return lines.join("\n")
}

function statusTone(status: Status): string {
  return status === "error" ? "error" : status === "off" ? "textMuted" : status === "generic" ? "warning" : status === "preview" ? "info" : "success"
}

function settingsSummary(api: any): string {
  const resolved = resolvedSettings(api)
  const override = sessionOverride(api, currentSessionID(api))
  const settings = { ...resolved.settings, ...override }
  return `${short(settings.behavior)} · ${short(settings.scope)} · ${short(settings.qualityGate)} · ${resolved.source === "default" ? "Default" : TARGET_LABELS[Object.keys(override).some(key => key !== "schemaVersion") ? "session" : resolved.source]}`
}

function SettingsDialog(props: { api: any; target: Target }): any {
  const api = props.api
  const openBehavior = () => api.ui.dialog.replace(() => <api.ui.DialogSelect title="Behavior" current={(sessionOverride(api, currentSessionID(api)).behavior ?? resolvedSettings(api).settings.behavior)} options={[
    { title: "Auto", value: "auto", description: "Optimize when the quality gate says it helps." },
    { title: "Preview", value: "preview", description: "Show the suggested flow before execution." },
    { title: "Off", value: "off", description: "Keep Prompt Optimizer disabled." },
  ]} onSelect={(option: any) => saveSetting(api, props.target, "behavior", option.value)} />)
  const openScope = () => api.ui.dialog.replace(() => <api.ui.DialogSelect title="Scope" options={[
    { title: "First request", value: "first", description: "Apply only to the first user request." },
    { title: "All requests", value: "all", description: "Apply throughout the session." },
  ]} onSelect={(option: any) => saveSetting(api, props.target, "scope", option.value)} />)
  const openGate = () => api.ui.dialog.replace(() => <api.ui.DialogSelect title="Quality gate" options={[
    { title: "Adaptive", value: "adaptive", description: "Choose PASS, LIGHT or FULL from task complexity." },
    { title: "Pass", value: "pass", description: "Use the legacy always-normalize path." },
    { title: "Light", value: "light", description: "Use a concise normalization." },
    { title: "Full", value: "full", description: "Use the complete execution brief." },
  ]} onSelect={(option: any) => saveSetting(api, props.target, "qualityGate", option.value)} />)
  const openUnsupported = () => api.ui.dialog.replace(() => <api.ui.DialogSelect title="Unsupported model" options={[
    { title: "Skip", value: "skip", description: "Do not optimize models outside the registry." },
    { title: "Generic fallback", value: "generic", description: "Use model-neutral optimization guidance." },
  ]} onSelect={(option: any) => saveSetting(api, props.target, "unsupportedModel", option.value)} />)
  const settings = { ...resolvedSettings(api).settings, ...sessionOverride(api, currentSessionID(api)) }
  return <api.ui.DialogSelect title={`Prompt Optimizer · ${settingsSummary(api)}`} options={[
    { title: `Behavior · ${short(settings.behavior)}`, value: "behavior", description: "Auto, preview or off." },
    { title: `Scope · ${short(settings.scope)}`, value: "scope", description: "First request or all requests." },
    { title: `Quality gate · ${short(settings.qualityGate)}`, value: "qualityGate", description: "How much normalization to apply." },
    { title: `Unsupported model · ${short(settings.unsupportedModel)}`, value: "unsupportedModel", description: "Fallback behavior for unknown models." },
    { title: `Save to · ${TARGET_LABELS[props.target]}`, value: "target", description: "Choose where the next changes are saved." },
    { title: "Done", value: "done", description: "Close Prompt Optimizer settings." },
  ]} onSelect={(option: any) => {
    if (option.value === "behavior") openBehavior()
    else if (option.value === "scope") openScope()
    else if (option.value === "qualityGate") openGate()
    else if (option.value === "unsupportedModel") openUnsupported()
    else if (option.value === "target") openTarget(api)
    else api.ui.dialog.clear()
  }} />
}

function openTarget(api: any): void {
  const options: Array<{ title: string; value: Target; description: string }> = [
    { title: "Session", value: "session", description: "Temporary; applies only to this OpenCode session." },
    { title: "Project", value: "project", description: "Save in .opencode/prompt-optimizer.json." },
    { title: "Global", value: "global", description: "Save in ~/.config/opencode/prompt-optimizer.json." },
  ]
  api.ui.dialog.replace(() => <api.ui.DialogSelect title="Choose save target" options={options} onSelect={(option: any) => {
    if (option.value === "session" && !currentSessionID(api)) {
      api.ui.toast({ variant: "warning", title: "Prompt Optimizer", message: "Open a session to use session settings." })
      return
    }
    api.ui.dialog.replace(() => <SettingsDialog api={api} target={option.value} />)
  }} />)
}

function saveSetting(api: any, target: Target, key: keyof Settings, value: string): void {
  try {
    if (target === "session") {
      const sessionID = currentSessionID(api)
      if (!sessionID) throw new Error("Open a session to use session settings")
      saveSession(sessionID, { [key]: value })
    } else updateConfig(paths(api)[target], { [key]: value })
    api.ui.dialog.replace(() => <SettingsDialog api={api} target={target} />)
    api.ui.toast({ variant: "success", title: "Prompt Optimizer", message: `${short(key)} saved to ${TARGET_LABELS[target]}`, duration: 2200 })
  } catch (error) {
    api.ui.toast({ variant: "error", title: "Prompt Optimizer", message: String(error), duration: 3500 })
  }
}

function StatusWidget(props: { api: any; sessionID?: string }) {
  const current = statusFromConfig(props.api, props.sessionID)
  const theme = props.api.theme.current
  const override = sessionOverride(props.api, props.sessionID)
  const chip = formatStatusChip({ status: current.status, behavior: (override.behavior ?? resolvedSettings(props.api).settings.behavior), sessionOverride: Object.keys(override).some(key => key !== "schemaVersion") })
  const color = theme[chip.tone === "muted" ? "textMuted" : chip.tone] ?? theme.text
  return <text fg={color}>{chip.label}{chip.marker}</text>
}

const tui: TuiPlugin = async (api) => {
  const slots: TuiSlotPlugin = {
    slots: {
      home_prompt_right() {
        return <StatusWidget api={api} />
      },
      session_prompt_right(_ctx: any, value: { session_id: string }) {
        return <StatusWidget api={api} sessionID={value.session_id} />
      },
    },
  }
  api.slots.register(slots)

  api.keymap.registerLayer({
    mode: "base",
    commands: [
      {
        name: "prompt-optimizer.open",
        title: "Prompt Optimizer · Settings",
        description: "Configure Prompt Optimizer behavior and save target",
        category: "Plugin",
        namespace: "palette",
        slashName: "prompt-optimizer",
        slashAliases: ["po"],
        suggested: true,
        run() {
          api.ui.dialog.replace(() => <SettingsDialog api={api} target="global" />)
        },
      },
      {
        name: "prompt-optimizer.status",
        title: "Prompt Optimizer status",
        description: "Show current optimizer status",
        category: "Plugin",
        namespace: "palette",
         slashName: "po-status",
         run() {
           const sessionID = currentSessionID(api)
           api.ui.dialog.replace(() => <api.ui.DialogAlert title="Prompt Optimizer status" message={statusDetails(api, sessionID)} />)
         },
      },
    ],
    bindings: [{ key: "ctrl+shift+p", cmd: "prompt-optimizer.open", desc: "Open Prompt Optimizer settings" }],
  })
}

const plugin: TuiPluginModule & { id: string } = {
  id: "prompt-optimizer.tui",
  tui,
}

export default plugin
