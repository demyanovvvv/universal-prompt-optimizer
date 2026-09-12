import * as assert from "node:assert/strict"
import * as test from "node:test"

import plugin, { resolveModel } from "../adapters/opencode/plugin/index"
import { decide } from "../adapters/opencode/plugin/decision-engine"
import { chooseQualityGate } from "../adapters/opencode/plugin/quality-gate"
import { MAX_SESSIONS, STATE_TTL_MS, emptyMetrics, isDuplicate, isSessionExpired, pruneSessions } from "../adapters/opencode/plugin/session-state"
import { classifyTask } from "../adapters/opencode/plugin/task-classifier"
import type { Settings } from "../adapters/opencode/plugin/types"

const settings: Settings = {
  behavior: "auto",
  scope: "all",
  qualityGate: "adaptive",
  unsupportedModel: "skip",
}

test("model resolution preserves variant precedence and reports its source", () => {
  assert.deepEqual(resolveModel("anthropic", "claude-fable-5.1"), {
    profile: "claude-fable-5.1",
    confidence: "high",
    source: "exact-id",
    modelID: "claude-fable-5.1",
    matchedAlias: "claude-fable-5.1",
  })
  assert.equal(resolveModel("proxy", "vendor/GLM_5.3_FLASH-latest").profile, "glm-5.3-flash")
  assert.equal(resolveModel("deepseek", "deepseek-v4").profile, undefined)
  assert.equal(resolveModel("unknown", "model").source, "unsupported")
})

test("adaptive gate chooses pass, light, and full from deterministic signals", () => {
  assert.equal(chooseQualityGate("adaptive", { prompt: "Rename foo to bar." }), "pass")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Review this change", taskType: "review" }), "light")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Migrate every production schema", taskType: "migration" }), "full")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Do it", risk: "consequential" }), "full")
})

test("task classifier keeps security and migration precedence", () => {
  assert.deepEqual(classifyTask("Audit this OAuth permission vulnerability"), { type: "security", confidence: "medium" })
  assert.equal(classifyTask("Plan and implement the schema migration").type, "migration")
  assert.equal(classifyTask("Tell me the time").type, "unknown")
})

test("decision engine honors duplicate, off, scope, and generic fallback", () => {
  const base = { settings, scopeEligible: true, model: { providerID: "openai", modelID: "gpt-5.6" }, profile: "sol" as const }
  assert.equal(decide({ ...base, duplicate: true }, "Fix it").reason, "duplicate event")
  assert.equal(decide({ ...base, settings: { ...settings, behavior: "off" } }, "Fix it").action, "skip")
  assert.equal(decide({ ...base, scopeEligible: false }, "Fix it").action, "skip")
  const generic = decide({ ...base, profile: undefined, settings: { ...settings, unsupportedModel: "generic" } }, "Fix it")
  assert.equal(generic.profile, "generic")
  assert.match(generic.warning ?? "", /neutral guidance/)
})

test("session pruning expires stale entries and caps the map", () => {
  const now = Date.now()
  const sessions = new Map<string, { state: { userPromptCount: number; active: boolean; lastSeenAt: number } }>()
  sessions.set("stale", { state: { userPromptCount: 0, active: false, lastSeenAt: now - STATE_TTL_MS - 1 } })
  for (let index = 0; index < MAX_SESSIONS + 10; index++) {
    sessions.set(`session-${index}`, { state: { userPromptCount: 0, active: true, lastSeenAt: now + index } })
  }
  pruneSessions(sessions, now)
  assert.equal(sessions.has("stale"), false)
  assert.equal(sessions.size, MAX_SESSIONS)
  assert.equal(sessions.has("session-0"), false)
  assert.equal(sessions.has(`session-${MAX_SESSIONS + 9}`), true)
  assert.equal(isSessionExpired({ userPromptCount: 0, active: false, lastSeenAt: now - STATE_TTL_MS - 1 }), true)
})

test("hash duplicate fallback ignores the prompt reserved for the current turn", () => {
  const state = { userPromptCount: 1, active: true, metrics: emptyMetrics(), lastPromptHash: "ignored", lastProcessedEventId: "event-1" }
  assert.equal(isDuplicate(state, "event-1", "same"), true)
  assert.equal(isDuplicate({ ...state, lastProcessedEventId: undefined, pendingPromptHash: "reserved" }, undefined, "same"), false)
})

test("OpenCode hook applies once per message and respects scope=first", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "first", qualityGate: "adaptive", unsupportedModel: "skip" })
  const first = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "m1" }, { parts: [{ type: "text", text: "Rename foo to bar." }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, first)
  assert.equal(first.system.length, 1)
  assert.match(first.system[0], /Quality gate: PASS/)
  assert.match(first.system[0], /Preview enforcement: advisory/)

  const duplicate = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, duplicate)
  assert.equal(duplicate.system.length, 0)

  const second = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "m2" }, { parts: [{ type: "text", text: "Fix another bug" }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, second)
  assert.equal(second.system.length, 0)
})
