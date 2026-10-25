import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent"
import { registerOptimizer } from "./runtime"

export default function (pi: ExtensionAPI) {
  const z = pi.zod
  registerOptimizer(pi, z.object({ optimized_prompt: z.string().describe("The exact optimized prompt to execute after approval") }))
}
