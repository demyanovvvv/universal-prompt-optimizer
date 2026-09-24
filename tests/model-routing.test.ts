import * as assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import test from "node:test"
import { runInNewContext } from "node:vm"
import { ModuleKind, transpileModule } from "typescript"

import plugin, { resolveModel } from "../adapters/opencode/plugin/index"

const routes = [
  ["gpt-6-astra", "astra", "GPT-6 Astra"],
  ["gpt-6-sol", "sol", "GPT-6 Sol"],
  ["sol", "sol", "GPT-6 Sol"],
  ["gpt-6-luna", "luna", "GPT-6 Luna"],
  ["luna", "luna", "GPT-6 Luna"],
  ["gpt-5.6", "gpt-5.6-sol", "GPT-5.6 Sol"],
  ["gpt-5.6-sol", "gpt-5.6-sol", "GPT-5.6 Sol"],
  ["gpt-5.6-luna", "gpt-5.6-luna", "GPT-5.6 Luna"],
  ["gpt-5.6-terra", "terra", "GPT-5.6 Terra"],
  ["terra", "terra", "GPT-5.6 Terra"],
  ["claude-opus-5-5", "claude-opus-5.5", "Claude Opus 5.5"],
  ["claude-opus-5.5", "claude-opus-5.5", "Claude Opus 5.5"],
  ["claude-opus-5", "claude-opus-5", "Claude Opus 5"],
  ["claude-opus-4.8", "claude-opus-4.8", "Claude Opus 4.8"],
] as const

const unsupported = [
  "gpt-6", "gpt-6-terra", "gpt-60-sol", "gpt-5.60-sol",
  "gpt-6-sol-extra", "gpt-6-sol-2026", "gpt-5.6-luna-extra", "solvent", "unknown-model",
  "claude-opus-5.50", "claude-opus-5-50", "claude-opus-5-2026", "claude-opus-5.5-extra",
]

test("OpenCode routes GPT generations separately and injects the matching profile", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "all", qualityGate: "light", unsupportedModel: "skip" })
  for (const [id, profile, label] of routes) {
    for (const model of [id, `vendor/${id.toUpperCase().replace(/-/g, "_")}-latest`]) {
      assert.equal(resolveModel("sol", model).profile, profile, model)
      const output = { system: [] as string[] }
      await hooks["chat.message"]({ sessionID: model, messageID: "1" }, { parts: [{ type: "text", text: "Fix this parser bug." }] })
      await hooks["experimental.chat.system.transform"]({ sessionID: model, model: { providerID: "proxy", id: model } }, output)
      assert.ok(output.system.join("\n").includes(`${label}:`), model)
    }
  }
  for (const model of unsupported) assert.equal(resolveModel("sol", model).profile, undefined, model)
})

// Execute the shipped Pi extension with host registration/schema stubs and no
// user config. Routing and before_agent_start remain real; Pi is not a dependency.
function piHook() {
  const source = readFileSync(resolve(process.cwd(), "adapters/pi/extensions/prompt-optimizer.ts"), "utf8")
  const routingSource = readFileSync(resolve(process.cwd(), "adapters/pi/extensions/model-registry.ts"), "utf8")
  const routingCompiled = transpileModule(routingSource, { compilerOptions: { module: ModuleKind.CommonJS } }).outputText
  const routingExports: Record<string, unknown> = {}
  runInNewContext(routingCompiled, { exports: routingExports, require })
  const compiled = transpileModule(source, { compilerOptions: { module: ModuleKind.CommonJS } }).outputText
  const exports: { default?: (api: unknown) => void } = {}
  runInNewContext(compiled, {
    exports,
    require: (id: string) => {
      if (id === "typebox") return { Type: { Object: () => ({}), String: () => ({}) } }
      if (id === "node:fs") return { existsSync: () => false }
      if (id === "./model-registry") return routingExports
      return require(id)
    },
    process: { env: {} },
  })
  const hooks: Record<string, (event: unknown, ctx: unknown) => any> = {}
  exports.default!({ on: (name: string, handler: typeof hooks[string]) => { hooks[name] = handler }, registerTool() {}, registerCommand() {} })
  return hooks.before_agent_start
}

test("Pi routes GPT generations and aliases without cross-generation or provider matches", async () => {
  const hook = piHook()
  for (const [id, , label] of routes) {
    for (const model of [id, `vendor/${id.toUpperCase().replace(/-/g, "_")}-latest`]) {
      const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider: "proxy", id: model }, sessionManager: { getSessionId: () => model } })
      assert.ok(output?.systemPrompt.includes(`${label}:`), model)
    }
  }
  for (const model of unsupported) {
    const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider: "sol", id: model }, sessionManager: { getSessionId: () => model } })
    assert.equal(output, undefined, model)
  }
})
