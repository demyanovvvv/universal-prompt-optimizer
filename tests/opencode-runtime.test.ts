import * as assert from "node:assert/strict"
import test from "node:test"

import plugin, { promptText, resolveModel } from "../adapters/opencode/plugin/index"
import { decide } from "../adapters/opencode/plugin/decision-engine"
import { chooseQualityGate } from "../adapters/opencode/plugin/quality-gate"
import { MAX_SESSIONS, STATE_TTL_MS, emptyMetrics, isDuplicate, isSessionExpired, normalizeState, pruneSessions } from "../adapters/opencode/plugin/session-state"
import { classifyTask, analyzeTask } from "../adapters/opencode/plugin/task-classifier"
import { assessRisk } from "../adapters/opencode/plugin/risk-analysis"
import { TurnStore } from "../adapters/opencode/plugin/turn-store"
import { hasInvalidManagedFields, qualityGateFromEnvironment, resolveSettings } from "../adapters/opencode/plugin/config"
import { PREVIEW, PROFILE_HINTS, analyzePrompt, buildPromptPlan, renderPromptPlan } from "../adapters/opencode/plugin/prompt-builder"
import type { Settings } from "../adapters/opencode/plugin/types"
import { clearSessionSettings, configPathForTarget, loadManagedConfig, loadSessionSettings, updateManagedConfig } from "../adapters/opencode/plugin/tui-config"
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

const settings: Settings = {
  behavior: "auto",
  scope: "all",
  qualityGate: "adaptive",
  unsupportedModel: "skip",
}

test("TUI config targets resolve to project and global paths", () => {
  const projectRoot = "C:/workspace/demo"
  assert.equal(configPathForTarget(projectRoot, "project", "C:/Users/test"), join(projectRoot, ".opencode", "prompt-optimizer.json"))
  assert.equal(configPathForTarget(projectRoot, "global", "C:/Users/test"), join("C:/Users/test", ".config", "opencode", "prompt-optimizer.json"))
  assert.equal(configPathForTarget(projectRoot, "session", "C:/Users/test"), undefined)
})

test("/po-status is implemented as a native TUI information dialog", () => {
  const source = readFileSync(join(process.cwd(), "adapters/opencode/tui/prompt-optimizer.tsx"), "utf8")
  const statusCommand = source.indexOf('slashName: "po-status"')
  assert.notEqual(statusCommand, -1)
  const commandBlock = source.slice(statusCommand, source.indexOf("\n        },", statusCommand))
  assert.match(commandBlock, /api\.ui\.dialog\.replace\(\(\) => <api\.ui\.DialogAlert/)
  assert.doesNotMatch(commandBlock, /api\.ui\.toast/)
  assert.match(source, /Status: \$\{current\.label\}/)
})

test("prompt-optimizer.menu exposes a structured palette menu with subtitles", () => {
  const source = readFileSync(join(process.cwd(), "adapters/opencode/tui/prompt-optimizer.tsx"), "utf8").replace(/\r\n/g, "\n")
  const menuCommand = source.indexOf('name: "prompt-optimizer.menu"')
  assert.notEqual(menuCommand, -1)
  const commandBlock = source.slice(menuCommand, source.indexOf("\n      },", menuCommand))
  assert.match(commandBlock, /category: "Prompt Optimizer"/)
  assert.match(commandBlock, /namespace: "palette"/)
  assert.match(commandBlock, /run\(\) \{\s*openMenu\(api\)\s*\}/)
  // The menu command must not claim a slash name: /prompt-optimizer is served by
  // the server plugin, and a second registration would shadow it.
  assert.doesNotMatch(commandBlock, /slashName|slashAliases/)

  const menuStart = source.indexOf("function openMenu(api: any): void {")
  assert.notEqual(menuStart, -1)
  const menuBody = source.slice(menuStart, source.indexOf("\n}\n", menuStart))
  assert.match(menuBody, /api\.ui\.DialogSelect/)
  for (const [value, title] of [
    ["status", /Status · \$\{current\.label\}/],
    ["behavior", /Behavior · \$\{short\(settings\.behavior\)\}/],
    ["scope", /Scope · \$\{short\(settings\.scope\)\}/],
    ["qualityGate", /Quality gate · \$\{short\(settings\.qualityGate\)\}/],
    ["unsupportedModel", /Unsupported model · \$\{short\(settings\.unsupportedModel\)\}/],
    ["target", /Save to · \$\{TARGET_LABELS\[target\]\}/],
  ] as const) {
    assert.match(menuBody, new RegExp(`value: "${value}"`))
    assert.match(menuBody, title)
  }
  const rows = menuBody.match(/description:/g) ?? []
  assert.equal(rows.length, 7)
  assert.match(menuBody, /statusDetails\(api, sessionID\)/)
  for (const open of ["openBehavior", "openScope", "openGate", "openUnsupported"]) {
    assert.match(menuBody, new RegExp(`${open}\\(api, target\\)`))
  }
})

test("Prompt Optimizer keeps the host command palette and does not bind ctrl+p", () => {
  const source = readFileSync(join(process.cwd(), "adapters/opencode/tui/prompt-optimizer.tsx"), "utf8").replace(/\r\n/g, "\n")
  const bindings = source.slice(source.indexOf("bindings: ["))
  assert.match(bindings, /key: "ctrl\+shift\+p", cmd: "prompt-optimizer\.open"/)
  // ctrl+p is OpenCode's built-in command_list; binding it here would shadow the
  // host palette for the whole application.
  assert.doesNotMatch(bindings, /key: "ctrl\+p"/)
})

test("managed config updates preserve unknown fields and write atomically", () => {
  const root = mkdtempSync(join(tmpdir(), "prompt-optimizer-tui-"))
  const path = join(root, "prompt-optimizer.json")
  writeFileSync(path, JSON.stringify({ schemaVersion: 1, behavior: "off", custom: { keep: true } }), "utf8")

  const next = updateManagedConfig(path, { behavior: "auto", scope: "all" })

  assert.deepEqual(next, { schemaVersion: 1, behavior: "auto", custom: { keep: true }, scope: "all" })
  assert.deepEqual(loadManagedConfig(path), next)
  assert.equal(readFileSync(path, "utf8").endsWith("\n"), true)
})

test("session settings load by session ID and ignore invalid managed values", () => {
  const home = mkdtempSync(join(tmpdir(), "prompt-optimizer-session-"))
  const folder = join(home, ".config", "opencode", "prompt-optimizer-sessions")
  mkdirSync(folder, { recursive: true })
  const path = join(folder, `${encodeURIComponent("session/demo")}.json`)
  writeFileSync(path, JSON.stringify({ schemaVersion: 1, behavior: "preview", scope: "first" }))
  assert.deepEqual(loadSessionSettings("session/demo", home), { behavior: "preview", scope: "first" })
  writeFileSync(path, JSON.stringify({ schemaVersion: 1, behavior: "unknown" }))
  assert.deepEqual(loadSessionSettings("session/demo", home), {})
})


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

test("prompt analysis preserves explicit scope, constraints, and deliverables", () => {
  const analysis = analyzePrompt("Fix src/auth/callback.ts, preserve the public API, run tests/auth.test.ts, and report the root cause.")
  assert.equal(analysis.primaryTask, "bugfix")
  assert.equal(analysis.hasScope, true)
  assert.equal(analysis.hasConstraints, true)
  assert.equal(analysis.hasValidation, true)
  assert.equal(analysis.hasDeliverable, true)
  assert.match(analysis.exactLiterals.join(" "), /src\/auth\/callback\.ts/)
})

test("multi-axis analysis preserves mixed migration, security, planning, and implementation intent", () => {
  const analysis = analyzeTask("Plan and implement the schema migration, review security impact, preserve compatibility, and run the affected tests.")
  assert.equal(analysis.primaryType, "migration")
  assert.deepEqual(analysis.types, ["migration", "security", "review", "testing", "planning", "implementation"])
  assert.equal(analysis.executionIntent, "execute")
  assert.equal(analysis.confidence, "high")
})

test("policy precedence keeps safety and explicit read-only boundaries above task guidance", () => {
  const plan = buildPromptPlan({
    prompt: "Review the production deletion logic; do not modify files.",
    profile: "sol",
    behavior: "auto",
    qualityGate: "adaptive",
    gate: "full",
    taskType: "security",
  })
  const rendered = renderPromptPlan(plan)
  assert.match(rendered, /do not modify files/i)
  assert.match(rendered, /approval boundary/i)
  assert.doesNotMatch(rendered, /perform the smallest in-scope work/i)
})

test("risk analysis distinguishes negated dangerous words from authorized consequences", () => {
  assert.deepEqual(assessRisk("Review the deletion logic; do not delete anything"), {
    level: "none",
    categories: [],
    requiresApproval: false,
    evidence: [],
  })
  const mixed = assessRisk("Do not delete logs; remove the cache")
  assert.equal(mixed.level, "consequential")
  assert.ok(mixed.categories.includes("destructive"))
  const production = assessRisk("Delete all production records")
  assert.equal(production.level, "consequential")
  assert.equal(production.requiresApproval, true)
  assert.deepEqual(production.categories.sort(), ["destructive", "production"])
})

test("prompt analysis exposes missing high-value signals without copying the prompt", () => {
  const analysis = analyzePrompt("Fix the auth callback")
  assert.deepEqual(analysis.missingSignals, ["scope", "constraints", "validation", "deliverable"])
  const complete = analyzePrompt("Fix src/auth/callback.ts, preserve the API, run tests/auth.test.ts, and report the root cause")
  assert.deepEqual(complete.missingSignals, [])
})

test("corrupt metric enum values are discarded during state normalization", () => {
  const state = normalizeState({ userPromptCount: 1, active: true, metrics: { lastAction: "corrupt", lastGate: "corrupt", lastProfile: "corrupt" } })
  assert.equal(state?.metrics?.lastAction, undefined)
  assert.equal(state?.metrics?.lastGate, undefined)
  assert.equal(state?.metrics?.lastProfile, undefined)
})

test("Argon profile survives session override and resolution normalization", () => {
  const state = normalizeState({
    userPromptCount: 1, active: true,
    override: { profile: "gemini-4-argon" },
    lastResolution: { profile: "gemini-4-argon", source: "exact-id", confidence: "high", modelID: "gemini-4-argon" },
    metrics: { lastProfile: "gemini-4-argon" },
  })
  assert.equal(state?.override?.profile, "gemini-4-argon")
  assert.equal(state?.lastResolution?.profile, "gemini-4-argon")
  assert.equal(state?.metrics?.lastProfile, "gemini-4-argon")
})

test("turn store keeps interleaved turns correlated and consumes each turn once", () => {
  const store = new TurnStore()
  store.admit("session-1", { messageID: "a", prompt: "Fix A" })
  store.admit("session-1", { messageID: "b", prompt: "Fix B" })
  assert.equal(store.resolve("session-1", "a")?.prompt, "Fix A")
  assert.equal(store.resolve("session-1", "b")?.prompt, "Fix B")
  assert.equal(store.consume("session-1", "a")?.prompt, "Fix A")
  assert.equal(store.consume("session-1", "a"), undefined)
  assert.equal(store.size("session-1"), 1)
})

test("turn store preserves distinct fallback turns with identical timestamps and prompt prefixes", () => {
  const store = new TurnStore()
  store.admit("session-1", { prompt: "Repeated prompt with the same prefix" }, 1000)
  store.admit("session-1", { prompt: "Repeated prompt with the same prefix" }, 1000)
  assert.equal(store.size("session-1", 1000), 2)
  assert.equal(store.consume("session-1", undefined, 1001)?.prompt, "Repeated prompt with the same prefix")
  assert.equal(store.consume("session-1", undefined, 1002)?.prompt, "Repeated prompt with the same prefix")
  assert.equal(store.consume("session-1"), undefined)
})

test("turn store expires stale turns when they are read", () => {
  const store = new TurnStore(16, 10)
  store.admit("session-1", { messageID: "stale", prompt: "Expired" }, 1000)
  assert.equal(store.resolve("session-1", "stale"), undefined)
  assert.equal(store.resolve("session-1", "stale"), undefined)
  assert.equal(store.size("session-1"), 0)
  assert.equal(store.consume("session-1", "stale"), undefined)
})

test("duplicate message delivery does not block a later turn", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "all", qualityGate: "light", unsupportedModel: "generic" })
  const first = { system: [] as string[] }
  await hooks["chat.message"]({ sessionID: "duplicate-queue", messageID: "a" }, { parts: [{ type: "text", text: "Fix the auth callback." }] })
  await hooks["experimental.chat.system.transform"]({ sessionID: "duplicate-queue", model: { providerID: "openai", id: "gpt-5.6" } }, first)
  assert.equal(first.system.length, 1)

  await hooks["chat.message"]({ sessionID: "duplicate-queue", messageID: "a" }, { parts: [{ type: "text", text: "Fix the auth callback." }] })
  await hooks["chat.message"]({ sessionID: "duplicate-queue", messageID: "b" }, { parts: [{ type: "text", text: "Implement the cache helper." }] })
  const second = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "duplicate-queue", model: { providerID: "openai", id: "gpt-5.6" } }, second)
  assert.equal(second.system.length, 1)
  assert.match(second.system[0], /Implement the smallest coherent change/i)
})

test("prompt plan creates a bounded bugfix execution brief without generic chain of thought", () => {
  const plan = buildPromptPlan({
    prompt: "Fix the failing auth callback and run the affected test.",
    profile: "sol",
    behavior: "auto",
    qualityGate: "light",
    gate: "light",
    taskType: "bugfix",
  })
  const rendered = renderPromptPlan(plan)
  assert.match(rendered, /Objective/i)
  assert.match(rendered, /Validation/i)
  assert.match(rendered, /root cause/i)
  assert.doesNotMatch(rendered, /think step by step|chain.of.thought/i)
  assert.ok(rendered.length < 2400)
})

test("prompt plan keeps user data out of system authority and preserves a long request in its original message", () => {
  const prompt = "USER_DATA_SENTINEL " + "context ".repeat(1000) + "do not deploy"
  const plan = buildPromptPlan({ prompt, profile: "sol", behavior: "preview", qualityGate: "full", gate: "full", taskType: "bugfix" })
  const rendered = renderPromptPlan(plan)
  assert.equal(plan.prompt, prompt)
  assert.doesNotMatch(rendered, /USER_DATA_SENTINEL/)
  assert.match(rendered, /PREVIEW MODE/)
  assert.match(rendered, /Lifecycle:/)
  assert.ok(rendered.length <= 5000)
})

test("read-only and explanation briefs never prescribe code changes", () => {
  for (const prompt of ["Plan only: fix the bug, do not modify files", "Объясни ошибку, ничего не менять"]) {
    const plan = buildPromptPlan({ prompt, profile: "generic", behavior: "auto", qualityGate: "full", gate: "full", taskType: "bugfix" })
    const rendered = renderPromptPlan(plan)
    assert.match(rendered, /read-only/i)
    assert.doesNotMatch(rendered, /before changing code|fix issues caused by the change/)
  }
})

test("Russian completeness signals and off mode are respected", () => {
  const analysis = analyzePrompt("Исправь src/auth.ts, сохрани API, запусти тесты и составь отчёт")
  assert.equal(analysis.hasConstraints, true)
  assert.equal(analysis.hasValidation, true)
  assert.equal(analysis.hasDeliverable, true)
  assert.equal(renderPromptPlan(buildPromptPlan({ prompt: "Fix it", profile: "sol", behavior: "off", qualityGate: "full", gate: "full", taskType: "bugfix" })), "")
})

test("pass prompt plan stays empty in automatic mode", () => {
  const plan = buildPromptPlan({
    prompt: "Rename foo to bar.",
    profile: "sol",
    behavior: "auto",
    qualityGate: "adaptive",
    gate: "pass",
    taskType: "refactor",
  })
  assert.equal(renderPromptPlan(plan), "")
})

test("review plan forbids mutation unless explicitly requested", () => {
  const plan = buildPromptPlan({
    prompt: "Review src/auth for security issues and do not modify files.",
    profile: "sol",
    behavior: "auto",
    qualityGate: "full",
    gate: "full",
    taskType: "review",
  })
  const rendered = renderPromptPlan(plan)
  assert.match(rendered, /findings first/i)
  assert.match(rendered, /do not modify files/i)
})

test("adaptive gate escalates underspecified implementation requests without using length as complexity", () => {
  assert.equal(chooseQualityGate("adaptive", { prompt: "Fix the auth callback", taskType: "bugfix" }), "light")
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

test("unknown or missing models use generic structured guidance by default", () => {
  const base = {
    settings: { ...settings, unsupportedModel: "generic" as const },
    model: { providerID: "unknown", modelID: "big-pickle" },
    profile: undefined,
    taskType: "implementation" as const,
    risk: "none" as const,
    executionIntent: "explain" as const,
    duplicate: false,
    scopeEligible: true,
  }
  assert.equal(decide(base, "Build the feature").action, "apply")
  assert.equal(decide(base, "Build the feature").profile, "generic")
  assert.equal(decide({ ...base, model: { providerID: "", modelID: "" } }, "Build the feature").profile, "generic")
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

test("disabled pending turns cannot contaminate a later enabled turn", async () => {
  const hooks = await plugin.server({ directory: process.cwd() }, { behavior: "auto", scope: "all", qualityGate: "full", unsupportedModel: "generic" })
  await hooks["command.execute.before"]({ sessionID: "off-then-on", command: "po", arguments: "off" }, { parts: [] })
  await hooks["chat.message"]({ sessionID: "off-then-on", messageID: "old" }, { parts: [{ type: "text", text: "Review the security impact of this change." }] })
  const disabled = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "off-then-on", model: { providerID: "openai", id: "gpt-5.6" } }, disabled)
  assert.equal(disabled.system.length, 0)

  await hooks["command.execute.before"]({ sessionID: "off-then-on", command: "po", arguments: "auto" }, { parts: [] })
  await hooks["chat.message"]({ sessionID: "off-then-on", messageID: "new" }, { parts: [{ type: "text", text: "Implement the requested change." }] })
  const enabled = { system: [] as string[] }
  await hooks["experimental.chat.system.transform"]({ sessionID: "off-then-on", model: { providerID: "openai", id: "gpt-5.6" } }, enabled)
  assert.equal(enabled.system.length, 1)
  assert.doesNotMatch(enabled.system[0], /Report findings first/)
})

test("session settings can be cleared without leaving a persistent override", () => {
  const home = mkdtempSync(join(tmpdir(), "upo-session-reset-"))
  const sessionID = "persistent-reset"
  const sessionFile = join(home, ".config", "opencode", "prompt-optimizer-sessions", `${encodeURIComponent(sessionID)}.json`)
  mkdirSync(join(home, ".config", "opencode", "prompt-optimizer-sessions"), { recursive: true })
  writeFileSync(sessionFile, JSON.stringify({ schemaVersion: 1, behavior: "off" }))
  assert.equal(loadSessionSettings(sessionID, home).behavior, "off")
  clearSessionSettings(sessionID, home)
  assert.equal(loadSessionSettings(sessionID, home).behavior, undefined)
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
