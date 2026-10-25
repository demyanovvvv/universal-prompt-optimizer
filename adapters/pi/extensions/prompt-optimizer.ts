import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"
import { Type } from "typebox"
import { registerOptimizer } from "./prompt-optimizer/runtime"

export default function (pi: ExtensionAPI) {
  registerOptimizer(pi, Type.Object({ optimized_prompt: Type.String({ description: "The exact optimized prompt to execute after approval" }) }))
}
