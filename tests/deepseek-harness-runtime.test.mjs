import assert from 'node:assert/strict'
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { test } from 'node:test'

const packageRoot = fileURLToPath(new URL('../', import.meta.url))
const registry = JSON.parse(readFileSync(new URL('../.agents/skills/prompt-optimizer/references/model-registry.json', import.meta.url), 'utf8'))

// Each node:test file runs in its own process; isolate host-global config reads.
const home = mkdtempSync(join(tmpdir(), 'upo-dsh-home-'))
const oldHome = process.env.HOME
const oldProfile = process.env.USERPROFILE
process.env.HOME = home
process.env.USERPROFILE = home
process.on('exit', () => {
  if (oldHome === undefined) delete process.env.HOME
  else process.env.HOME = oldHome
  if (oldProfile === undefined) delete process.env.USERPROFILE
  else process.env.USERPROFILE = oldProfile
  rmSync(home, { recursive: true, force: true })
})

async function harness(t, config = {}) {
  const root = mkdtempSync(join(tmpdir(), 'upo-dsh-runtime-'))
  t.after(() => rmSync(root, { recursive: true, force: true }))
  const native = join(root, '.dsh')
  cpSync(join(packageRoot, 'adapters/deepseek-harness/plugin'), join(native, 'plugins/prompt-optimizer'), { recursive: true })
  cpSync(join(packageRoot, '.agents/skills/prompt-optimizer'), join(native, 'skills/prompt-optimizer'), { recursive: true })
  const configPath = join(root, '.prompt-optimizer.json')
  const globalPath = join(home, '.config/prompt-optimizer/config.json')
  rmSync(globalPath, { force: true })
  t.after(() => rmSync(globalPath, { force: true }))
  const setConfig = value => writeFileSync(configPath, JSON.stringify(value))
  setConfig(config)
  const plugin = await import(pathToFileURL(join(native, 'plugins/prompt-optimizer/index.mjs')).href)
  let section
  const ctx = {
    systemPrompt: { section(value) { assert.equal(section, undefined); section = value; return () => {} } },
    workingDirectory: { get(session) { return session.cwd } },
    agents: { turnBoundaryOf(session) { return { lastTurn: session.turn, openTurnStartSeq: session.turn * 100, lastStepStartSeq: session.step, lastStepBoundary: null } } },
  }
  plugin.apply(ctx)
  const agent = { session: { cwd: root, turn: 1, step: 1 }, options: { model: 'unknown-stale-model' } }
  const selection = { model: 'deepseek-flash', provider: 'deepseek-official', reasoningEffort: 'high' }
  const text = (snapshot = selection, currentAgent = agent) => section.text({ agent: currentAgent, modelSelection: snapshot })
  return { root, plugin, section, ctx, agent, selection, text, setConfig, configPath, globalPath }
}

test('Harness reads installed canonical profiles for every exact alias, without provider-based guesses', async t => {
  const h = await harness(t)
  for (const profile of registry.profiles) {
    const heading = readFileSync(join(packageRoot, '.agents/skills/prompt-optimizer/references', profile.file), 'utf8').split('\n')[0].replace(/^# /, '')
    for (const alias of profile.aliases) {
      for (const id of [alias, `provider/${alias}`, `${alias}-latest`, `provider/${alias.toUpperCase().replaceAll('-', '_')}`]) {
        assert.ok(h.text({ model: id, provider: 'irrelevant' }).includes(heading), id)
      }
    }
  }
  for (const model of ['deepseek-v4', 'deepseek-v4.1', 'deepseek-v4.1-flash-1017-extra', 'gemini-4-carbon-copy', 'glm-5.3-flashx-legal', 'muse-wonder-full', 'constructor', '__proto__', '']) {
    assert.equal(h.text({ model, provider: 'deepseek-flash' }), '', model)
  }
  assert.equal(h.text(null), '')
})

test('Harness does not mutate route, session, other sections or interpolate literal profile braces', async t => {
  const h = await harness(t)
  const before = JSON.stringify([h.selection, h.agent])
  assert.match(h.text(), /Preserve.*(?:intent|user)/i)
  assert.equal(JSON.stringify([h.selection, h.agent]), before)
  assert.equal(h.section.interpolate, false)
  assert.notEqual(h.section.complete, true)
  assert.equal(h.section.text({}), '')
  assert.deepEqual(new Set(h.plugin.inject), new Set(['systemPrompt', 'agents', 'workingDirectory']))
})

test('Harness OFF adds nothing and PREVIEW requires textual confirmation rather than a nonexistent tool', async t => {
  const h = await harness(t, { behavior: 'off' })
  assert.equal(h.text(), '')
  h.setConfig({ behavior: 'preview' })
  const preview = h.text()
  assert.match(preview, /PREVIEW/i)
  assert.match(preview, /exact.*(?:prompt|brief)/i)
  assert.match(preview, /(?:wait|stop).*confirm/i)
  assert.doesNotMatch(preview, /call prompt_optimizer_preview/)
  h.setConfig({ behavior: 'auto' })
  assert.match(h.text(), /AUTO/i)
  assert.doesNotMatch(h.text(), /PREVIEW MODE/)
})

test('Harness first scope follows durable turns across repeated assembly, tools, skipped and resumed turns', async t => {
  const h = await harness(t, { scope: 'first' })
  const first = h.text()
  assert.notEqual(first, '')
  h.agent.session.step = 2
  assert.equal(h.text(), first)
  h.agent.session.turn = 2
  assert.equal(h.text(), '')
  const resumed = { session: { cwd: h.root, turn: 12, step: 30 } }
  assert.equal(h.text(h.selection, resumed), '')
  h.agent.session.turn = 1
  assert.equal(h.text({ model: 'unknown', provider: 'deepseek' }), '')
  h.agent.session.turn = 2
  assert.equal(h.text(), '')
  h.agent.session.turn = 1
  h.setConfig({ scope: 'first', behavior: 'off' })
  assert.equal(h.text(), '')
  h.agent.session.turn = 2
  h.setConfig({ scope: 'first', behavior: 'auto' })
  assert.equal(h.text(), '')
})

test('Harness generic fallback is neutral even when provider names a known model', async t => {
  const h = await harness(t, { unsupportedModel: 'generic' })
  for (const snapshot of [{ model: 'future-model', provider: 'gpt-6.1-sol' }, null]) {
    const text = h.text(snapshot)
    assert.notEqual(text, '')
    assert.match(text, /(?:generic|neutral)/i)
    assert.doesNotMatch(text, /GPT-6\.1 Sol|DeepSeek V4\.1 Flash prompt profile/)
  }
})
test('Harness applies explicit quality gates and accepts legacy boolean values', async t => {
  const h = await harness(t)
  for (const [gate, expected] of [['light', /LIGHT/], ['full', /FULL/], ['adaptive', /PASS.*LIGHT.*FULL/], ['pass', /(?:leanest|normaliz)/i], [true, /PASS.*LIGHT.*FULL/], [false, /(?:leanest|normaliz)/i]]) {
    h.setConfig({ qualityGate: gate })
    assert.match(h.text(), expected, String(gate))
  }
})

test('Harness PREVIEW retains every selected gate without granting automatic execution', async t => {
  const h = await harness(t)
  for (const [gate, token] of [['light', 'LIGHT'], ['full', 'FULL'], ['pass', 'PASS'], ['adaptive', 'ADAPTIVE'], [true, 'ADAPTIVE'], [false, 'PASS']]) {
    h.setConfig({ behavior: 'preview', qualityGate: gate })
    const text = h.text()
    assert.ok(text.includes(`Quality gate ${token}`), String(gate))
    assert.match(text, /PREVIEW/)
    assert.doesNotMatch(text, /Then execute in this same turn/)
    assert.match(text, /stop and wait for the confirmation/)
  }
})

test('Harness fails closed when active directory or first-turn state cannot be read', async t => {
  const h = await harness(t, { scope: 'first' })
  for (const value of [undefined, '', 42]) {
    h.ctx.workingDirectory.get = () => value
    assert.equal(h.text(), '')
  }
  h.ctx.workingDirectory.get = () => { throw new Error('working directory unavailable') }
  assert.equal(h.text(), '')
  h.ctx.workingDirectory.get = session => session.cwd
  h.ctx.agents.turnBoundaryOf = () => { throw new Error('boundary unavailable') }
  assert.equal(h.text(), '')
})

test('Harness merges valid project settings over global and reads each active session directory', async t => {
  const h = await harness(t, { qualityGate: 'light', behavior: 'auto' })
  mkdirSync(join(home, '.config/prompt-optimizer'), { recursive: true })
  writeFileSync(h.globalPath, JSON.stringify({ behavior: 'off', scope: 'first', qualityGate: 'full', unrelated: true }))
  assert.match(h.text(), /LIGHT/)
  h.agent.session.turn = 2
  assert.equal(h.text(), '')
  h.agent.session.turn = 1
  const other = join(h.root, 'other-project')
  mkdirSync(other)
  h.agent.session.cwd = other
  assert.equal(h.text(), '')
  writeFileSync(join(other, '.prompt-optimizer.json'), JSON.stringify({ behavior: 'auto', scope: 'all' }))
  h.agent.session.turn = 2
  assert.match(h.text(), /FULL/)
})

test('Harness fails closed for invalid or unreadable config in either source', async t => {
  const h = await harness(t)
  const invalid = [[], null, 1, { schemaVersion: true }, { schemaVersion: 2 }, { behavior: 'on' }, { scope: 'second' }, { qualityGate: 1 }, { unsupportedModel: 'guess' }, { mode: 'preview' }]
  for (const value of invalid) {
    h.setConfig(value)
    assert.equal(h.text(), '', JSON.stringify(value))
  }
  writeFileSync(h.configPath, '{broken')
  assert.equal(h.text(), '')
  h.setConfig({ behavior: 'auto', qualityGate: 'adaptive' })
  mkdirSync(join(home, '.config/prompt-optimizer'), { recursive: true })
  writeFileSync(h.globalPath, '{broken')
  assert.equal(h.text(), '')
  rmSync(h.globalPath)
  mkdirSync(h.globalPath)
  assert.equal(h.text(), '')
  rmSync(h.globalPath, { recursive: true })
})
