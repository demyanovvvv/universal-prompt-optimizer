import * as assert from "node:assert/strict"
import test from "node:test"

import { normalizeModelID, resolvePiProfile } from "../adapters/pi/extensions/model-registry"

test("Pi routing uses the exact shared aliases and supported latest suffix", () => {
  assert.equal(resolvePiProfile("vendor/GLM_5.3_FLASH-latest"), "glm-5.3-flash")
  assert.equal(resolvePiProfile("claude-fable-5.1"), "claude-fable-5.1")
  assert.equal(resolvePiProfile("claude-fable-5.10"), undefined)
  assert.equal(resolvePiProfile("glm-5.30"), undefined)
  assert.equal(resolvePiProfile("constructor"), undefined)
})

test("Pi model normalization accepts malformed inputs as unsupported IDs", () => {
  assert.equal(normalizeModelID(undefined), "")
  assert.equal(normalizeModelID("provider/model_latest"), "model-latest")
})
