import * as assert from "node:assert/strict"
import test from "node:test"

import plugin, { promptText, resolveModel } from "../adapters/opencode/plugin/index"
import { decide } from "../adapters/opencode/plugin/decision-engine"
import { chooseQualityGate } from "../adapters/opencode/plugin/quality-gate"
import { MAX_SESSIONS, STATE_TTL_MS, emptyMetrics, isDuplicate, isSessionExpired, pruneSessions } from "../adapters/opencode/plugin/session-state"
import { classifyTask } from "../adapters/opencode/plugin/task-classifier"
import { hasInvalidManagedFields, qualityGateFromEnvironment, resolveSettings } from "../adapters/opencode/plugin/config"
import { PREVIEW, PROFILE_HINTS } from "../adapters/opencode/plugin/prompt-builder"
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
  assert.equal(resolveModel("proxy", "qwen3.8-max-2026-09-02").profile, "qwen3.8-max")
  assert.equal(resolveModel("proxy", "hy-4-preview").profile, "hy4-preview")
  assert.equal(resolveModel("deepseek", "deepseek-v4").profile, undefined)
  assert.equal(resolveModel("unknown", "model").source, "unsupported")
  assert.equal(resolveModel("anthropic", "claude-fable-5.10").profile, undefined)
  assert.equal(resolveModel("proxy", "glm-5.30").profile, undefined)
  assert.equal(resolveModel("astra", "unknown-model").profile, undefined)
})

test("invalid plugin options fail closed rather than silently enabling defaults", () => {
  const resolved = resolveSettings(process.cwd(), { behavior: "invalid" }, {})
  assert.equal(resolved.invalidConfig, true)
  assert.equal(resolved.behavior, "off")
})

test("invalid managed config cannot be overridden back to AUTO for the same turn", async () => {
  const { mkdtempSync, writeFileSync, rmSync } = await import("node:fs")
  const { tmpdir } = await import("node:os")
  const { join } = await import("node:path")
  const project = mkdtempSync(join(tmpdir(), "upo-invalid-config-"))
  try {
    writeFileSync(join(project, ".prompt-optimizer.json"), JSON.stringify({ behavior: "unexpected" }))
    const hooks = await plugin.server({ directory: project }, undefined)
    await hooks["chat.message"]({ sessionID: "override-session", messageID: "m1" }, { message: { role: "user", id: "m1", model: { providerID: "openai", modelID: "gpt-6-sol" }, parts: [{ type: "text", text: "Inspect the repository" }] } })
    const output: any = { system: [] }
    await hooks["experimental.chat.system.transform"]({ sessionID: "override-session", model: { providerID: "openai", id: "gpt-6-sol" } }, output)
    assert.deepEqual(output.system, [])
  } finally {
    rmSync(project, { recursive: true, force: true })
  }
})

test("model lookup does not resolve inherited object properties as profiles", () => {
  assert.equal(resolveModel("provider", "constructor").profile, undefined)
  assert.equal(resolveModel("provider", "toString").profile, undefined)
})

test("managed config rejects non-string enum values", () => {
  assert.equal(hasInvalidManagedFields({ behavior: ["off"] }), true)
  assert.equal(hasInvalidManagedFields({ scope: { value: "all" } }), true)
  assert.equal(hasInvalidManagedFields({ qualityGate: ["full"] }), true)
})

test("invalid quality gate environment values are not treated as adaptive", () => {
  assert.equal(qualityGateFromEnvironment("not-a-gate"), undefined)
  assert.equal(qualityGateFromEnvironment("off"), "pass")
})

test("task classifier recognizes Russian analysis requests", () => {
  const result = classifyTask("Проанализируй проект, что нужно исправить, что улучшить, предложи улучшения")
  assert.equal(result.type, "review")
})

test("prompt extraction preserves ordered text parts without duplicating message text", () => {
  assert.equal(promptText({
    message: { content: "Fix the auth bug." },
    parts: [
      { type: "text", text: "Fix the auth bug." },
      { type: "tool", text: "ignored tool output" },
      { type: "text", text: "Only edit src/auth and run the security tests." },
    ],
  }), "Fix the auth bug.\n\nOnly edit src/auth and run the security tests.")
})

test("adaptive gate chooses pass, light, and full from deterministic signals", () => {
  assert.equal(chooseQualityGate("adaptive", { prompt: "Rename foo to bar." }), "pass")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Review this change", taskType: "review" }), "light")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Migrate every production schema", taskType: "migration" }), "full")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Do it", risk: "consequential" }), "full")
  assert.equal(chooseQualityGate("adaptive", { prompt: "Delete all production records" }), "full")
  assert.equal(chooseQualityGate("adaptive", { prompt: "План миграции базы данных, ничего не менять", taskType: "planning" }), "light")
})

test("task classifier keeps security and migration precedence", () => {
  assert.deepEqual(classifyTask("Audit this OAuth permission vulnerability"), { type: "security", confidence: "medium" })
  assert.equal(classifyTask("Plan and implement the schema migration").type, "migration")
  assert.equal(classifyTask("Tell me the time").type, "unknown")
  assert.equal(classifyTask("Migrate the credentials table").type, "migration")
  assert.equal(classifyTask("Удалить все записи в production").risk, "consequential")
  assert.equal(classifyTask("Plan only, do not modify files").executionIntent, "plan")
  assert.equal(classifyTask("Do not print credentials while fixing this local bug").risk, undefined)
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

test("GPT-6 Sol repository analysis is explicitly bounded at observable completion", () => {
  assert.match(PROFILE_HINTS.sol, /bounded inspection/i)
  assert.match(PROFILE_HINTS.sol, /stop.*tool/i)
  assert.match(PROFILE_HINTS.sol, /acceptance criteria/i)
})

test("PREVIEW explicitly stops before mutation when approval is unavailable", () => {
  assert.match(PREVIEW, /Do not call mutation-capable tools before approval/i)
  assert.match(PREVIEW, /stop/i)
  assert.match(PREVIEW, /Never pretend approval occurred|explicit confirmation/i)
})

test("OpenCode system transform carries Sol bounded-analysis and preview safety guidance", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "preview", scope: "all", qualityGate: "adaptive", unsupportedModel: "skip" })
  const output = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "sol-preview", messageID: "m1" }, { parts: [{ type: "text", text: "Analyze the repository and report the three highest-risk integration issues." }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "sol-preview", model: { providerID: "omniroute", id: "vilao/gpt-6-sol" } }, output)
  assert.equal(output.system.length, 1)
  assert.match(output.system[0], /bounded inspection/i)
  assert.match(output.system[0], /Do not call mutation-capable tools before approval/i)
})

test("OpenCode hook leaves adaptive PASS out of model context and respects scope=first", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "first", qualityGate: "adaptive", unsupportedModel: "skip" })
  const first = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "m1" }, { parts: [{ type: "text", text: "Rename foo to bar." }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, first)
  assert.equal(first.system.length, 0)

  const duplicate = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, duplicate)
  assert.equal(duplicate.system.length, 0)

  const second = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "s1", messageID: "m2" }, { parts: [{ type: "text", text: "Fix another bug" }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "s1", model: { providerID: "openai", id: "gpt-5.6" } }, second)
  assert.equal(second.system.length, 0)
})

test("scope=first is reserved until a supported model turn is processed", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "first", qualityGate: "adaptive", unsupportedModel: "skip" })
  await hooks["chat.message"]({ sessionID: "scope-late", messageID: "m1" }, { parts: [{ type: "text", text: "Migrate every production schema and run the migration tests." }] })
  const unsupported = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "scope-late", model: { providerID: "unknown", id: "unlisted-model" } }, unsupported)
  assert.equal(unsupported.system.length, 0)

  await hooks["chat.message"]({ sessionID: "scope-late", messageID: "m2" }, { parts: [{ type: "text", text: "Migrate every production schema and run the migration tests." }] })
  const supported = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "scope-late", model: { providerID: "openai", id: "gpt-5.6" } }, supported)
  assert.equal(supported.system.length, 1)
})

test("OpenCode injects lean LIGHT guidance without session diagnostics", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, settings)
  const output = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "light", messageID: "m1" }, { parts: [{ type: "text", text: "Review this change" }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "light", model: { providerID: "openai", id: "gpt-6-astra" } }, output)
  assert.equal(output.system.length, 1)
  assert.match(output.system[0], /Selected quality gate: LIGHT/)
  assert.match(output.system[0], /GPT-6 Astra/)
  assert.doesNotMatch(output.system[0], /Prompt Optimizer decision/)
  assert.doesNotMatch(output.system[0], /Session totals/)
  assert.doesNotMatch(output.system[0], /Config status/)
  assert.ok(output.system[0].length < 1800)
})

test("explicit pass setting retains always-normalize behavior", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { ...settings, qualityGate: "pass" })
  const output = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "legacy-pass", messageID: "m1" }, { parts: [{ type: "text", text: "Rename foo to bar." }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "legacy-pass", model: { providerID: "openai", id: "gpt-6-astra" } }, output)
  assert.equal(output.system.length, 1)
  assert.match(output.system[0], /Quality gate is disabled/)
  assert.match(output.system[0], /Selected quality gate: PASS/)
})
