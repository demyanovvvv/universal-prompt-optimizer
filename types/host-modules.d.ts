declare module "@opencode-ai/plugin" {
  export const Plugin: any
}

declare module "@opencode-ai/plugin/v2/promise" {
  export function define<T>(plugin: T): T
}

declare module "@opencode-ai/plugin/tui" {
  export type TuiPlugin = (api: any, options?: Record<string, unknown>, meta?: Record<string, unknown>) => Promise<void> | void
  export type TuiPluginModule = { id?: string; tui: TuiPlugin; server?: never }
  export type TuiSlotPlugin = { slots: Record<string, (...args: any[]) => unknown>; order?: number }
}

declare module "@opentui/solid/jsx-runtime" {
  export const jsx: (...args: any[]) => JSX.Element
  export const jsxs: (...args: any[]) => JSX.Element
  export const Fragment: unknown
}

declare namespace JSX {
  interface Element {}
  interface IntrinsicElements {
    box: any
    text: any
  }
}

declare module "@earendil-works/pi-coding-agent" {
  export type ExtensionAPI = any
}

declare module "@oh-my-pi/pi-coding-agent" {
  export type ExtensionAPI = any
}

declare module "typebox" {
  export const Type: any
}
