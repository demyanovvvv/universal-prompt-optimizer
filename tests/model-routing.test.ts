import * as assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import test from "node:test"
import { runInNewContext } from "node:vm"
import { ModuleKind, transpileModule } from "typescript"

import plugin, { resolveModel } from "../adapters/opencode/plugin/index"
import { PROFILE_HINTS } from "../adapters/opencode/plugin/prompt-builder"

// [model id handed to the host, expected profile, expected injected label]
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
  ["claude-sonnet-5.5", "claude-sonnet-5.5", "Claude Sonnet 5.5"],
  ["claude-sonnet-5-5", "claude-sonnet-5.5", "Claude Sonnet 5.5"],
  ["gpt-6.1-sol", "gpt-6.1-sol", "GPT-6.1 Sol"],
  ["deepseek-v4.1-flash", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["deepseek-v4-1-flash", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["deepseek-flash", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["deepseek-v4.1-flash-1017", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["deepseek-v4-1-flash-1017", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["deepseek-v4-flash", "deepseek-v4-flash", "DeepSeek V4 Flash"],
  ["deepseek-v4-pro", "deepseek-v4-pro", "DeepSeek V4 Pro"],
  ["gemini-4-argon", "gemini-4-argon", "Gemini 4 Argon"],
  ["gemini-4-hydrogen", "gemini-4-hydrogen", "Gemini 4 Hydrogen"],
  ["google/gemini-4-hydrogen", "gemini-4-hydrogen", "Gemini 4 Hydrogen"],
  ["gemini-4-carbon", "gemini-4-carbon", "Gemini 4 Carbon"],
  ["claude-fable-5.2", "claude-fable-5.2", "Claude Fable 5.2"],
  ["claude-fable-5-2", "claude-fable-5.2", "Claude Fable 5.2"],
  ["anthropic/claude-fable-5-2", "claude-fable-5.2", "Claude Fable 5.2"],
  ["z-ai/glm-5.3-flashx", "glm-5.3-flashx", "GLM-5.3 FlashX"],
  ["glm-5-3-flashx", "glm-5.3-flashx", "GLM-5.3 FlashX"],
  ["moonshotai/kimi-k3.1-pro", "kimi-k3.1-pro", "Kimi K3.1 Pro"],
  ["kimi-k3-1-pro", "kimi-k3.1-pro", "Kimi K3.1 Pro"],
  ["minimax/minimax-m3.1-flash", "minimax-m3.1-flash", "MiniMax M3.1 Flash"],
  ["minimax-m3-1-flash", "minimax-m3.1-flash", "MiniMax M3.1 Flash"],
  ["deepseek/deepseek-v4.1-flash", "deepseek-v4.1-flash", "DeepSeek V4.1 Flash"],
  ["meta/muse-wonder", "muse-wonder", "Muse Wonder"],
  ["muse-wonder-1.0", "muse-wonder", "Muse Wonder"],
  ["meta/muse-wonder-1-0", "muse-wonder", "Muse Wonder"],
  ["google/gemini-4-argon", "gemini-4-argon", "Gemini 4 Argon"],
  ["claude-fable-5.1", "claude-fable-5.1", "Claude Fable 5.1"],
  ["claude-fable-5", "claude-fable-5", "Claude Fable 5"],
  ["glm-5.3", "glm-5.3", "GLM-5.3"],
  ["glm-5.3-flash", "glm-5.3-flash", "GLM-5.3 Flash"],
  ["kimi-k3", "kimi-k3", "Kimi K3"],
  ["muse-spark-1.3", "muse-spark-1.3", "Muse Spark 1.3"],
  ["google/gemini-3.8-flash", "gemini-3.8-flash", "Gemini 3.8 Flash"],
  ["grok-4.6", "grok-4.6", "Grok 4.6"],
] as const

const unsupported = [
  "gemini-4", "gemini-4.0-argon", "gemini-4-argol", "gemini-4-argon-cyber-permissive", "gemini-4-argon-extra",
  "gemini-4-hydrogen-extra", "gemini-4-hydrogens", "gemini-4-carbon-copy", "gemini-40-hydrogen", "gemini-4.0-hydrogen",
  "gpt-6", "gpt-6-terra", "gpt-60-sol", "gpt-5.60-sol",
  "gpt-6-sol-extra", "gpt-6-sol-2026", "gpt-5.6-luna-extra", "solvent", "unknown-model",
  "claude-opus-5.50", "claude-opus-5-50", "claude-opus-5-2026", "claude-opus-5.5-extra",
  "claude-sonnet-5.50", "claude-sonnet-5-50", "claude-sonnet-5.5-extra", "gpt-6.1-sol-extra", "gpt-6.1-sol-2026",
  "deepseek-v4", "deepseek-v4.1", "deepseek-v4.10-flash", "deepseek-v4-flash-extra",
  "deepseek-v4.1-flash-1018", "deepseek-v4.1-flash-10170", "deepseek-v4.1-flashi", "deepseek-flashx",
  "claude-fable", "claude-fable-5.2-extra", "claude-fable-5.20", "claude-fable-5.1-extra", "claude-fable-5x",
  "glm-5", "glm-5.3-flashxx", "glm-5.30-flashx", "glm-5.3-flashh",
  "kimi-k3.1", "kimi-k3.10-pro", "kimi-k3.1-pro-extra", "kimi-k3-pro", "kimi-k31-pro",
  "minimax-m3.1", "minimax-m3", "minimax-m3.1-flash-extra", "minimax-m3.10-flash", "minimax-m31-flash",
  "glm-5.3-flashx-legal", "glm-5.3-flashx-legals", "glm-50-flashx", "muse-wonder-1.0.1", "muse-wonders-1.0",
  "muse", "muse-spark", "muse-wonder-1.1", "muse-wonder-extra", "muse-wonder-full", "muse-wonderful", "muse-wonders",
  "deepseek-v4.1-flash-1017-extra", "gemini-4-argon-1017",
]

test("OpenCode routes every supported generation to its own profile and injects only that profile's hint", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "all", qualityGate: "light", unsupportedModel: "skip" })
  for (const [id, profile, label] of routes) {
    const hint = PROFILE_HINTS[profile]
    // Every other profile's hint is a distinct string; none of them may be
    // injected for this model. Labels are prefixes of each other (Fable 5 is a
    // prefix of Fable 5.1/5.2, K3 of K3.1 Pro), so compare whole hints.
    const foreign = Object.entries(PROFILE_HINTS)
      .filter(([key]) => key !== profile)
      .map(([, text]) => text)
      .filter(text => text !== hint)
    for (const model of [id, `vendor/${id.toUpperCase().replace(/-/g, "_")}-latest`]) {
      const resolution = resolveModel("sol", model)
      assert.equal(resolution.profile, profile, model)
      const output = { system: [] as string[] }
      await hooks["chat.message"]({ sessionID: model, messageID: "1" }, { parts: [{ type: "text", text: "Fix this parser bug." }] })
      await hooks["experimental.chat.system.transform"]({ sessionID: model, model: { providerID: "proxy", id: model } }, output)
      const rendered = output.system.join("\n")
      assert.ok(rendered.includes(hint), `${model} must inject the ${profile} hint`)
      assert.ok(rendered.includes(`${label}:`), `${model} must inject the ${label} label`)
      for (const other of foreign) assert.ok(!rendered.includes(other), `${model} leaked another profile's guidance`)
      assert.match(rendered, /Objective:/)
      assert.match(rendered, /Validation:/)
      assert.match(rendered, /Completion:/)
    }
  }
  for (const model of unsupported) assert.equal(resolveModel("sol", model).profile, undefined, model)
})

test("OpenCode keeps less specific profiles when a family-specific sibling exists", () => {
  assert.equal(resolveModel("z-ai", "glm-5.3-flash").profile, "glm-5.3-flash")
  assert.match(PROFILE_HINTS["glm-5.3-flash"], /^GLM-5\.3 Flash:/)
  assert.equal(resolveModel("z-ai", "glm-5.3-flashx").profile, "glm-5.3-flashx")
  assert.equal(resolveModel("anthropic", "claude-fable-5").profile, "claude-fable-5")
  assert.equal(resolveModel("google", "gemini-3.8-flash").profile, "gemini-3.8-flash")
  assert.equal(resolveModel("z-ai", "glm-5.3").profile, "glm-5.3")
  assert.equal(resolveModel("moonshotai", "kimi-k3").profile, "kimi-k3")
  assert.equal(resolveModel("meta", "muse-spark-1.3").profile, "muse-spark-1.3")
  assert.match(PROFILE_HINTS["muse-spark-1.3"], /^Muse Spark 1\.3:/)
  assert.equal(resolveModel("anthropic", "claude-fable-5.1").profile, "claude-fable-5.1")
  assert.equal(resolveModel("anthropic", "claude-fable-5").profile, "claude-fable-5")
  assert.equal(resolveModel("anthropic", "claude-fable-5.2").profile, "claude-fable-5.2")
  assert.equal(resolveModel("google", "gemini-4-argon").profile, "gemini-4-argon")
  assert.equal(resolveModel("google", "gemini-4-carbon").profile, "gemini-4-carbon")
  // Provider names are never model aliases: a provider called hydrogen or muse reveals nothing.
  assert.equal(resolveModel("hydrogen", "unknown").profile, undefined)
  assert.equal(resolveModel("muse-wonder", "unknown").profile, undefined)
})

// Execute the shipped Pi extension with host registration/schema stubs and no
// user config. Routing and before_agent_start remain real; Pi is not a dependency.
function piHook() {
  const source = readFileSync(resolve(process.cwd(), "adapters/pi/extensions/prompt-optimizer/runtime.ts"), "utf8")
  const routingSource = readFileSync(resolve(process.cwd(), "adapters/pi/extensions/model-registry.ts"), "utf8")
  const routingCompiled = transpileModule(routingSource, { compilerOptions: { module: ModuleKind.CommonJS } }).outputText
  const routingExports: Record<string, unknown> = {}
  runInNewContext(routingCompiled, { exports: routingExports, require })
  const compiled = transpileModule(source, { compilerOptions: { module: ModuleKind.CommonJS } }).outputText
  const exports: { registerOptimizer?: (api: unknown, parameters: unknown) => void } = {}
  runInNewContext(compiled, {
    exports,
    require: (id: string) => {
      if (id === "typebox") return { Type: { Object: () => ({}), String: () => ({}) } }
      if (id === "node:fs") return { existsSync: () => false, readFileSync: require(id).readFileSync }
      if (id === "../model-registry") return routingExports
      return require(id)
    },
    process: { env: {} },
  })
  const hooks: Record<string, (event: unknown, ctx: unknown) => any> = {}
  exports.registerOptimizer!({ on: (name: string, handler: typeof hooks[string]) => { hooks[name] = handler }, registerTool() {}, registerCommand() {} }, {})
  assert.equal(typeof hooks.session_shutdown, 'function', 'Pi must register the real cleanup event')
  return hooks.before_agent_start
}

// The Pi/OMP runtime ships its own hint table. Every newly supported profile must
// land on its own hint there too. GLM-5.3 and GLM-5.3 Flash deliberately share one
// documented combined "GLM-5.3 or GLM-5.3-Flash" hint and are asserted below.
const COMBINED_GLM_HINTS: Record<string, true> = { "glm-5.3": true, "glm-5.3-flash": true }
const piRoutes = routes.filter(([, profile]) => COMBINED_GLM_HINTS[profile] === undefined)

test("Pi routes each supported generation to its own profile hint without cross-generation matches", async () => {
  const hook = piHook()
  for (const [id, profile, label] of piRoutes) {
    for (const model of [id, `vendor/${id.toUpperCase().replace(/-/g, "_")}-latest`]) {
      const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider: "proxy", id: model }, sessionManager: { getSessionId: () => model } })
      assert.ok(output, model)
      assert.ok(output.systemPrompt.includes(`${label}:`), `${model} must inject ${label} guidance`)
    }
  }
  for (const model of ["glm-5.3", "glm-5.3-flash", "vendor/GLM_5.3_FLASH-latest"]) {
    const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider: "proxy", id: model }, sessionManager: { getSessionId: () => model } })
    assert.ok(output?.systemPrompt.includes("GLM-5.3 or GLM-5.3-Flash:"), model)
    assert.ok(!output.systemPrompt.includes("GLM-5.3 FlashX:"), model)
  }

  for (const model of unsupported) {
    const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider: "sol", id: model }, sessionManager: { getSessionId: () => model } })
    assert.equal(output, undefined, model)
  }
  for (const provider of ["hydrogen", "muse-wonder", "glm-5.3-flashx", "kimi-k3.1-pro"]) {
    const output = await hook({ systemPrompt: "original" }, { cwd: process.cwd(), model: { provider, id: "unknown" }, sessionManager: { getSessionId: () => provider } })
    assert.equal(output, undefined, provider)
  }
})
