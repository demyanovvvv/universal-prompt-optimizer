/** @jsxImportSource @opentui/solid */
import type { TuiPlugin, TuiPluginModule, TuiSlotPlugin } from "@opencode-ai/plugin/tui"

type Status = "enabled" | "preview" | "off" | "generic" | "error"

function statusFromConfig(api: any): { status: Status; label: string } {
  const config = api.tuiConfig ?? {}
  const override = api.kv?.get?.("prompt-optimizer/tui", {}) ?? {}
  if (override?.behavior === "off") return { status: "off", label: "PO x OFF" }
  if (override?.behavior === "preview") return { status: "preview", label: "PO o PREVIEW" }
  if (override?.profile === "generic") return { status: "generic", label: "PO ? GENERIC" }
  if (config?.plugin_enabled?.["prompt-optimizer-v5-5"] === false || config?.plugin_enabled?.["prompt-optimizer-v5-5.tui"] === false) return { status: "off", label: "PO x OFF" }
  return { status: "enabled", label: "PO + AUTO" }
}

function StatusWidget(props: { api: any }) {
  const current = statusFromConfig(props.api)
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
      session_prompt_right() {
        return <StatusWidget api={api} />
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
          const current = statusFromConfig(api)
          api.ui.toast({
            variant: current.status === "error" ? "error" : current.status === "generic" ? "warning" : "info",
            title: "Prompt Optimizer",
            message: `${current.label}. Use /prompt-optimizer status for detailed session state.`,
            duration: 3500,
          })
        },
      },
    ],
    bindings: [{ key: "ctrl+shift+p", cmd: "prompt-optimizer.open", desc: "Open Prompt Optimizer" }],
  })
}

const plugin: TuiPluginModule & { id: string } = {
  id: "prompt-optimizer-v5-5.tui",
  tui,
}

export default plugin
