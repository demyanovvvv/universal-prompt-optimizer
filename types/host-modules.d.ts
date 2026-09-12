declare module "@opencode-ai/plugin" {
  export const Plugin: any
}

declare module "@opencode-ai/plugin/tui" {
  export type TuiPlugin = any
  export type TuiPluginModule = any
  export type TuiSlotPlugin = any
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

declare module "typebox" {
  export const Type: any
}
