import * as assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import test from "node:test"

import { decide } from "../adapters/opencode/plugin/decision-engine"
import { chooseQualityGate } from "../adapters/opencode/plugin/quality-gate"
import { classifyTask } from "../adapters/opencode/plugin/task-classifier"
import { resolveModel } from "../adapters/opencode/plugin/index"
import type { Settings } from "../adapters/opencode/plugin/types"

type Contract = {
  profile?: string | null
  taskType?: string
  risk?: "none" | "consequential"
  executionIntent?: "execute" | "plan" | "review" | "explain"
  gate?: "pass" | "light" | "full"
  action?: "apply" | "preview" | "skip"
}

const settings: Settings = {
  behavior: "auto",
  scope: "all",
  qualityGate: "adaptive",
  unsupportedModel: "skip",
}

const cases = readFileSync(resolve(__dirname, "..", "..", "..", "evals/cases.jsonl"), "utf8")
  .split(/\r?\n/)
  .filter(Boolean)
  .map(line => JSON.parse(line) as { id: string; model: string; provider?: string; request: string; contract?: Contract })
  .filter(item => item.contract)

for (const fixture of cases) {
  test(`behavioral contract: ${fixture.id}`, () => {
    const resolution = resolveModel(fixture.provider ?? "fixture", fixture.model)
    const task = classifyTask(fixture.request)
    const expected = fixture.contract as Contract

    if ("profile" in expected) assert.equal(resolution.profile ?? null, expected.profile)
    if (expected.taskType) assert.equal(task.type, expected.taskType)
    if (expected.risk) assert.equal(task.risk ?? "none", expected.risk)
    if (expected.executionIntent) assert.equal(task.executionIntent, expected.executionIntent)
    if (expected.gate) {
      assert.equal(chooseQualityGate("adaptive", {
        prompt: fixture.request,
        taskType: task.type,
        risk: task.risk,
        executionIntent: task.executionIntent,
      }), expected.gate)
    }
    if (expected.action) {
      const decision = decide({
        settings,
        scopeEligible: true,
        model: { providerID: fixture.provider ?? "fixture", modelID: fixture.model },
        profile: resolution.profile,
        taskType: task.type,
        risk: task.risk,
        executionIntent: task.executionIntent,
      }, fixture.request)
      assert.equal(decision.action, expected.action)
    }
  })
}
