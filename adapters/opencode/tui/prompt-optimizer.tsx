/** @jsxImportSource @opentui/solid */
import type { TuiPlugin, TuiPluginModule, TuiSlotPlugin } from "@opencode-ai/plugin/tui"

type Status = "enabled" | "preview" | "off" | "generic" | "error"

function sessionDecision(api: any, sessionID?: string): any {
  if (!sessionID) return api.kv?.get?.("prompt-optimizer/decision", undefined)
  return api.kv?.get?.(`prompt-optimizer/decision/${sessionID}`, undefined)
}

function statusFromConfig(api: any, sessionID?: string): { status: Status; label: string } {
  const config = api.tuiConfig ?? {}
  const override = api.kv?.get?.("prompt-optimizer/tui", {}) ?? {}
  // The server plugin stores session state in server storage, not in the TUI
  // session object. Keep the widget config-level by default; use only explicit
  // TUI KV state when another integration publishes a decision summary.
  const decision = sessionDecision(api, sessionID)
  if (override?.behavior === "off") return { status: "off", label: "PO x OFF" }
  if (override?.behavior === "preview") return { status: "preview", label: "PO o PREVIEW" }
  if (override?.profile === "generic") return { status: "generic", label: "PO ? GENERIC" }
  if (config?.plugin_enabled?.["prompt-optimizer"] === false || config?.plugin_enabled?.["prompt-optimizer.tui"] === false || config?.plugin_enabled?.["prompt-optimizer-v5-5"] === false || config?.plugin_enabled?.["prompt-optimizer-v5-5.tui"] === false) return { status: "off", label: "PO x OFF" }
  if (decision?.action === "preview") return { status: "preview", label: "PO o PREVIEW" }
  if (decision?.profile === "generic") return { status: "generic", label: "PO ? GENERIC" }
  return { status: "enabled", label: "PO + AUTO" }
}

function statusDetails(api: any, sessionID?: string): string {
  const current = statusFromConfig(api, sessionID)
  const decision = sessionDecision(api, sessionID)
  const parts = [current.label]
  if (current.status === "preview") parts.push("PREVIEW advisory")
  if (decision?.profile) parts.push(`profile=${decision.profile}`)
  if (decision?.gate) parts.push(`gate=${decision.gate}`)
  if (decision?.reason) parts.push(`reason=${decision.reason}`)
  return parts.join("; ")
}

function StatusWidget(props: { api: any; sessionID?: string }) {
  const current = statusFromConfig(props.api, props.sessionID)
  const theme = props.api.theme.current
  const color = current.status === "error" ? theme.error : current.status === "off" ? theme.textMuted : current.status === "generic" ? theme.warning : current.status === "preview" ? theme.info : theme.success
  const override = props.api.kv?.get?.("prompt-optimizer/tui", {}) ?? {}
  const suffix = override?.behavior || override?.scope || override?.qualityGate || override?.profile ? " *" : ""
  return <text fg={color}>{current.label}{suffix}</text>
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
        title: "Prompt Optimizer",
        description: "Open Prompt Optimizer controls",
        category: "Plugin",
        namespace: "palette",
        slashName: "prompt-optimizer",
        slashAliases: ["po"],
        suggested: true,
        run() {
          api.ui.toast({
            variant: "info",
            title: "Prompt Optimizer",
            message: "Use /prompt-optimizer status, explain, on, off, preview, or reset.",
            duration: 4500,
          })
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
           const route = api.route?.current as { name?: string; params?: Record<string, unknown> } | undefined
           const sessionID = route?.name === "session" ? String(route.params?.sessionID ?? "") : undefined
           const current = statusFromConfig(api, sessionID)
          api.ui.toast({
            variant: current.status === "error" ? "error" : current.status === "generic" ? "warning" : "info",
            title: "Prompt Optimizer",
             message: `${statusDetails(api, sessionID)}. Use /prompt-optimizer status for detailed session state.`,
            duration: 3500,
          })
        },
      },
    ],
    bindings: [{ key: "ctrl+shift+p", cmd: "prompt-optimizer.open", desc: "Open Prompt Optimizer" }],
  })
}

const plugin: TuiPluginModule & { id: string } = {
  id: "prompt-optimizer.tui",
  tui,
}

export default plugin
