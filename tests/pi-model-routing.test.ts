import * as assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import test from "node:test"

import { normalizeModelID, resolvePiProfile } from "../adapters/pi/extensions/model-registry"

const registry = JSON.parse(readFileSync(resolve(process.cwd(), ".agents/skills/prompt-optimizer/references/model-registry.json"), "utf8")) as {
  profiles: { id: string; aliases: string[] }[]
}

test("Pi resolves every registry alias to its own profile, including provider-prefixed and -latest forms", () => {
  for (const profile of registry.profiles) {
    for (const alias of profile.aliases) {
      assert.equal(resolvePiProfile(alias), profile.id, alias)
      assert.equal(resolvePiProfile(`vendor/${alias.toUpperCase().replace(/-/g, "_")}-latest`), profile.id, alias)
    }
  }
  // Requested exact leaves stay pinned to their own profile, not a neighbour.
  assert.equal(resolvePiProfile("gemini-4-hydrogen"), "gemini-4-hydrogen")
  assert.equal(resolvePiProfile("google/gemini-4-hydrogen"), "gemini-4-hydrogen")
  assert.equal(resolvePiProfile("gemini-4-carbon"), "gemini-4-carbon")
  assert.equal(resolvePiProfile("claude-fable-5.2"), "claude-fable-5.2")
  assert.equal(resolvePiProfile("anthropic/claude-fable-5-2"), "claude-fable-5.2")
  assert.equal(resolvePiProfile("z-ai/glm-5.3-flashx"), "glm-5.3-flashx")
  assert.equal(resolvePiProfile("moonshotai/kimi-k3.1-pro"), "kimi-k3.1-pro")
  assert.equal(resolvePiProfile("minimax/minimax-m3.1-flash"), "minimax-m3.1-flash")
  assert.equal(resolvePiProfile("deepseek/deepseek-v4.1-flash-1017"), "deepseek-v4.1-flash")
  assert.equal(resolvePiProfile("deepseek-v4-1-flash-1017"), "deepseek-v4.1-flash")
  assert.equal(resolvePiProfile("meta/muse-wonder"), "muse-wonder")
  assert.equal(resolvePiProfile("muse-wonder-1.0"), "muse-wonder")
  assert.equal(resolvePiProfile("google/gemini-4-argon"), "gemini-4-argon")
})

test("Pi routing uses the exact shared aliases and supported latest suffix", () => {
  assert.equal(resolvePiProfile("vendor/GLM_5.3_FLASH-latest"), "glm-5.3-flash")
  assert.equal(resolvePiProfile("claude-fable-5.1"), "claude-fable-5.1")
  assert.equal(resolvePiProfile("claude-fable-5.10"), undefined)
  assert.equal(resolvePiProfile("glm-5.30"), undefined)
  assert.equal(resolvePiProfile("constructor"), undefined)
  assert.equal(resolvePiProfile("google/gemini-4-argon"), "gemini-4-argon")
  assert.equal(resolvePiProfile("gemini-4-argon-cyber-permissive"), undefined)
})

test("Pi rejects unknown suffixes, family-only and near-version ids for the new profiles", () => {
  for (const model of [
    "gemini-4-hydrogen-extra", "gemini-4-hydrogens", "gemini-4-carbon-copy", "gemini-40-carbon", "gemini-4",
    "claude-fable", "claude-fable-5.2-extra", "claude-fable-5.20", "claude-fable-5x",
    "glm-5", "glm-5.3-flashxx", "glm-5.30-flashx", "glm-5.3-flashh",
    "glm-5.3-flashx-legal", "glm-5.3-flashx-legals", "glm-50-flashx",
    "kimi-k3.1", "kimi-k3.10-pro", "kimi-k3-pro", "kimi-k3.1-pro-extra",
    "minimax-m3.1", "minimax-m3", "minimax-m3.1-flash-extra", "minimax-m3.10-flash",
    "muse", "muse-spark", "muse-wonder-1.1", "muse-wonder-extra", "muse-wonder-full", "muse-wonderful",
    "muse-wonder-1.0.1", "muse-wonders-1.0",
    "deepseek-v4.1-flash-1018", "deepseek-v4.1-flash-10170", "deepseek-flashx",
  ]) {
    assert.equal(resolvePiProfile(model), undefined, model)
  }
})
