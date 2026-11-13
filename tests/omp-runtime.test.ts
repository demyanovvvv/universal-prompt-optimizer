import { test, type TestContext } from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import omp from "../adapters/omp/extensions/prompt-optimizer/index"

import type { RuntimeContext, RuntimeTool, RuntimeCommand } from "../adapters/omp/extensions/prompt-optimizer/runtime"

// Newly supported exact profiles (leaf ids) and the labels the shipped runtime
// must inject for them.
const profileLabels = [
  ["gemini-4-hydrogen", "Gemini 4 Hydrogen"],
  ["google/gemini-4-hydrogen", "Gemini 4 Hydrogen"],
  ["gemini-4-carbon", "Gemini 4 Carbon"],
  ["claude-fable-5.2", "Claude Fable 5.2"],
  ["claude-fable-5-2", "Claude Fable 5.2"],
  ["glm-5.3-flashx", "GLM-5.3 FlashX"],
  ["z-ai/GLM_5.3_FLASHX-latest", "GLM-5.3 FlashX"],
  ["kimi-k3.1-pro", "Kimi K3.1 Pro"],
  ["moonshotai/kimi-k3-1-pro-latest", "Kimi K3.1 Pro"],
  ["minimax-m3.1-flash", "MiniMax M3.1 Flash"],
  ["muse-wonder", "Muse Wonder"],
  ["meta/muse-wonder-1.0", "Muse Wonder"],
] as const

function harness(t: TestContext, config: unknown = {}) {
  const root = mkdtempSync(join(tmpdir(), "upo-omp-"))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  t.mock.method(require("node:os"), "homedir", () => root)
  writeFileSync(join(root, ".prompt-optimizer.json"), JSON.stringify(config))
  const handlers: Record<string, (event: { systemPrompt: string }, ctx: RuntimeContext) => Promise<{ systemPrompt: string } | void>> = {}
  let tool!: RuntimeTool
  let command!: RuntimeCommand
  const schema = { object: (shape: unknown) => shape, string: () => ({ describe: () => ({ type: "string" }) }) }
  omp({ zod: schema, on: (name: string, fn: typeof handlers[string]) => { handlers[name] = fn }, registerTool: (value: RuntimeTool) => { tool = value }, registerCommand: (_name: string, value: RuntimeCommand) => { command = value } })
  const ctx: RuntimeContext = { cwd: root, model: { id: "gpt-6-sol", provider: "test" }, hasUI: true, sessionManager: { getSessionId: () => "same-id" }, ui: { notify() {}, confirm: async () => true, editor: async () => undefined } }
  return { handlers, tool, command, ctx, root, start: () => handlers.before_agent_start({ systemPrompt: "HOST POLICY" }, ctx) }
}

test("OMP registers native zod tool and preserves host prompt with exact routing", async t => {
  const h = harness(t)
  assert.deepEqual(h.tool.parameters, { optimized_prompt: { type: "string" } })
  const result = await h.start()
  assert.ok(result)
  assert.match(result.systemPrompt, /^HOST POLICY\n\n/)
  assert.match(result.systemPrompt, /GPT-6 Sol/)
  h.ctx.model = { id: "unknown", provider: "sol" }
  assert.equal(await h.start(), undefined)
  h.ctx.model.id = "gpt-6-sol-extra"
  assert.equal(await h.start(), undefined)
})

test("invalid config remains OFF despite session AUTO override", async t => {
  const h = harness(t, { scope: "invalid" })
  await h.command.handler("auto", h.ctx)
  assert.equal(await h.start(), undefined)
  writeFileSync(join(h.root, ".prompt-optimizer.json"), "{broken")
  assert.equal(await h.start(), undefined)
})

test("first scope counts unsupported turns and OFF turns", async t => {
  const h = harness(t, { scope: "first" })
  h.ctx.model.id = "unknown"
  assert.equal(await h.start(), undefined)
  h.ctx.model.id = "gpt-6-sol"
  assert.equal(await h.start(), undefined)
  await h.handlers.session_shutdown({ systemPrompt: "" }, h.ctx)
  await h.command.handler("off", h.ctx)
  await h.start()
  await h.command.handler("auto", h.ctx)
  assert.equal(await h.start(), undefined)
})

test("generic fallback is explicit and state is factory-local", async t => {
  const a = harness(t, { unsupportedModel: "generic" })
  const b = harness(t, { unsupportedModel: "generic" })
  await a.command.handler("off", a.ctx)
  assert.equal(await a.start(), undefined)
  b.ctx.model.id = "unknown"
  const result = await b.start()
  assert.ok(result)
  assert.match(result.systemPrompt, /Neutral model fallback/)
})

test("PREVIEW approves exactly once and rejects noneligible calls", async t => {
  const h = harness(t, { behavior: "preview" })
  await h.start()
  const invoke = () => h.tool.execute("id", { optimized_prompt: "Exact prompt" }, undefined, undefined, h.ctx)
  assert.equal((await invoke()).details.approved, true)
  assert.equal((await invoke()).details.approved, false)
  await h.start()
  h.ctx.hasUI = false
  assert.match((await invoke()).content[0].text, /PREVIEW_UNAVAILABLE/)
  h.ctx.hasUI = true
  h.ctx.ui.confirm = async () => false
  h.ctx.ui.editor = async () => "Edited prompt"
  assert.equal((await invoke()).details.prompt, "Edited prompt")
  await h.command.handler("off", h.ctx)
  assert.equal((await invoke()).details.approved, false)
})

test("global invalid configuration cannot be masked by project settings", async t => {
  const h = harness(t, { behavior: "auto" })
  const dir = join(h.root, ".config", "prompt-optimizer")
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, "config.json"), JSON.stringify({ schemaVersion: 2 }))
  assert.equal(await h.start(), undefined)
})

test("OMP injects each newly supported profile hint after the host prompt", async t => {
  const h = harness(t, { qualityGate: "full" })
  for (const [id, label] of profileLabels) {
    h.ctx.model = { id, provider: "proxy" }
    const result = await h.start()
    assert.ok(result, id)
    assert.match(result.systemPrompt, /^HOST POLICY\n\n/, id)
    assert.ok(result.systemPrompt.includes(`${label}:`), `${id} must inject ${label} guidance`)
    assert.match(result.systemPrompt, /Prompt Optimizer v5\.14/)
    assert.match(result.systemPrompt, /Preserve intent, exact literals, hard constraints/)
  }
})

test("OMP leaves unknown variants to the unsupported-model policy", async t => {
  const h = harness(t)
  for (const id of [
    "gemini-4-hydrogen-extra", "gemini-4-hydrogens", "gemini-4-carbon-copy", "glm-5.3-flashxx",
    "glm-5.3-flashh", "glm-5.3-flashx-legal", "glm-5.3-flashx-legals", "glm-5.30-flashx",
    "kimi-k3.1", "kimi-k3.10-pro", "kimi-k3-pro", "minimax-m3.1", "minimax-m31-flash",
    "muse", "muse-spark", "muse-wonder-1.1", "muse-wonder-extra", "muse-wonder-full", "muse-wonderful",
    "claude-fable-5.2-extra", "claude-fable-5.20", "deepseek-v4.1-flash-1018",
  ]) {
    h.ctx.model = { id, provider: "proxy" }
    assert.equal(await h.start(), undefined, id)
  }
  h.ctx.model = { id: "unknown", provider: "muse-wonder" }
  assert.equal(await h.start(), undefined)
})

test("OMP generic fallback stays model-agnostic for a newly supported leaf", async t => {
  const h = harness(t, { unsupportedModel: "generic" })
  h.ctx.model = { id: "muse-wonder-extra", provider: "meta" }
  const result = await h.start()
  assert.ok(result)
  assert.match(result.systemPrompt, /^HOST POLICY\n\n/)
  assert.match(result.systemPrompt, /Neutral model fallback/)
  assert.doesNotMatch(result.systemPrompt, /Muse Wonder/)
})
