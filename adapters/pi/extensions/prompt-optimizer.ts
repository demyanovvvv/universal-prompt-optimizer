import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"
import { Type } from "typebox"
import { existsSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

type Behavior = "auto" | "preview" | "off"
type Scope = "first" | "all"
type QualityGate = "pass" | "light" | "full" | "adaptive"
const sessionBehaviors = new Map<string, Behavior>()
const sessionTurns = new Map<string, number>()
const previewedTurns = new Map<string, number>()

const BASE_COMMON = `Preserve intent, exact literals, hard constraints, project rules, required verification and approval boundaries; do not invent requirements. Keep prompts as lean as the task/model permits. Native Reasoning First: no hidden-CoT requests or generic 'think step by step'. User instructions override this preflight.`
const BASE_GATE = `Prompt Optimizer v5.5: use PASS/LIGHT/FULL quality gating. ${BASE_COMMON}`
const BASE_ALWAYS = `Prompt Optimizer v5.5: quality gate is disabled; normalize every in-scope prompt into the leanest model-appropriate execution brief. ${BASE_COMMON}`
const PREVIEW = `PREVIEW MODE: before mutating/external work, form the exact optimized execution prompt and call prompt_optimizer_preview exactly once for this user-turn. Read-only context resolution may happen first. After tool approval, execute the returned approved/edited prompt; do not preview again in the same user-turn.`

const hints: Array<[RegExp,string]> = [
  [/claude.*fable.*5[.-]1/, "Claude Fable 5.1: end-to-end authorized work; targeted edits; batch independent tools; scope/test guard; preserve constraints in compaction; progress only when useful; Claude XML/examples/long-context ordering conditionally."],
  [/claude.*fable.*5/, "Claude Fable 5: objective/why/context/boundaries/acceptance; high autonomy; tool-grounded progress; conditional periodic spec verification on long runs; strong scope guard; no legacy microsteps/reasoning extraction."],
  [/^claude-opus-5[.-]5$/, "Claude Opus 5.5: complete task and observable done criteria; continue authorized reversible work; preserve required checks; use targeted evidence/review and mark unconfirmed findings; no generic think-hard scaffolding."],
  [/^claude-opus-5$/, "Claude Opus 5: complete task spec upfront; strong scope; keep required checks but suppress generic re-verification/verifier-agent scaffolding."],
  [/^claude-opus-4[.-]8$/, "Claude Opus 4.8: literal explicit scope propagation; require tool evidence when needed; concrete frontend design direction; review behavior/test failures without vague severity filtering."],
  [/claude.*sonnet.*5/, "Claude Sonnet 5: direct task, explicit affected scope/constraints/acceptance; literal propagation; concrete review failure criteria; no legacy thinking-budget/CoT."],
  [/glm.*5[.-]3(?:[-_]flash)?$/, "GLM-5.3 or GLM-5.3-Flash: outcome/context/hard constraints/acceptance/autonomous end-to-end; avoid microstep scaffolding."],
  [/glm.*5[.-]2$/, "GLM-5.2: inspect architecture/dependencies/interfaces; short plan if useful; implement and run relevant validation."],
  [/deepseek.*4.*flash/, "DeepSeek V4 Flash: compact direct task/context/constraints/required verification/done; no manual CoT."],
  [/deepseek.*4.*pro/, "DeepSeek V4 Pro: complete objective/context/scope/non-negotiable constraints/acceptance; autonomous debug/validation; no manual CoT."],
  [/kimi.*k.*3/, "Kimi K3: compact objective/context/constraints/acceptance, end-to-end autonomy; reasoning history is harness-only."],
  [/muse.*spark.*1[.-]3/, "Muse Spark 1.3: why/inputs/objective/deliverable/structure/audience/quality, not tool choreography; genuine questions/consequential confirmation."],
  [/hy.*4.*preview/, "Hy4-preview: direct goal/boundaries/done/stop; suppress overthinking and repeated generic verification."],
  [/qwen.*3[.-]8.*max/, "Qwen3.8-Max: goal/context/constraints/acceptance + autonomous tool-feedback loop; no repeated manual decomposition; clear tools."],
  [/gemini.*3[.-]8[-_]flash$/, "Gemini 3.8 Flash: very concise/direct, PASS/LIGHT aggressively; long context first, task at end; avoid verbose legacy frameworks."],
  [/grok.*4[.-]6/, "Grok 4.6: direct objective/context/constraints/evidence-tool policy/acceptance; native reasoning handles depth."],
  [/^(?:gpt-6-astra|astra)$/, "GPT-6 Astra: lean scope and explicit done boundary; for authorized implementation/bugfix work continue through implementation, inspection, fixes caused by the change, and affected validation; avoid needless approval, repo-wide reading, and generic over-testing."],
  [/^(?:gpt-6-sol|sol)$/, "GPT-6 Sol: preserve decisive context, hard constraints, approval boundaries and observable completion; infer routine intent and follow through on authorized work with proportionate validation."],
  [/^(?:gpt-6-luna|luna)$/, "GPT-6 Luna: compact bounded brief with one outcome, decisive context, hard constraints, exact output shape when needed, and correctness-critical validation."],
  [/^gpt-5\.6-luna$/, "GPT-5.6 Luna: leanest bounded GPT-5.6 brief without losing correctness-critical context."],
  [/^gpt-5\.6(?:-sol)?$/, "GPT-5.6 Sol: lean outcome-focused brief, decisive context, autonomy/approval boundaries, success criteria, focused tools."],
  [/^(?:gpt-5\.6-terra|terra)$/, "GPT-5.6 Terra: lean complete brief, one instruction once, autonomy/approval boundaries, focused tools, proportionate validation."],
]

function normalizeQualityGate(value: any): QualityGate | undefined {
  if (["pass", "light", "full", "adaptive"].includes(value)) return value as QualityGate
  if (typeof value === "boolean") return value ? "adaptive" : "pass"
  return undefined
}

function gateInstructions(gate: QualityGate): { base: string; mode: string } {
  if (gate === "pass") return {
    base: BASE_ALWAYS,
    mode: "AUTO MODE: normalize every in-scope prompt and execute immediately.",
  }
  if (gate === "light") return {
    base: BASE_GATE,
    mode: "Selected quality gate: LIGHT. Add only a missing high-value boundary, constraint, done criterion, approval boundary, or output shape, then execute immediately.",
  }
  if (gate === "full") return {
    base: BASE_GATE,
    mode: "Selected quality gate: FULL. Build a concise execution brief from only task-relevant context before executing immediately.",
  }
  return {
    base: BASE_GATE,
    mode: "AUTO MODE: silently optimize only when the quality gate says it helps and execute immediately.",
  }
}

function cfg(ctx: any): { behavior: Behavior; scope: Scope; qualityGate: QualityGate; unsupportedModel: "skip"|"generic" } {
  const sid = String(ctx.sessionManager?.getSessionId?.() ?? "__default__")
  const paths = [join(homedir(), ".config", "prompt-optimizer", "config.json"), join(ctx.cwd, ".prompt-optimizer.json")]
  let data:any = {}
  let invalidConfig = false
  for (const p of paths) if (existsSync(p)) {
    try {
      const parsed = JSON.parse(readFileSync(p,'utf8'))
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) { invalidConfig = true; continue }
       if (("behavior" in parsed && (typeof parsed.behavior !== "string" || !["auto","preview","off"].includes(parsed.behavior)))
        || ("schemaVersion" in parsed && (typeof parsed.schemaVersion !== 'number' || parsed.schemaVersion !== 1))
         || ("scope" in parsed && (typeof parsed.scope !== "string" || !["first","all"].includes(parsed.scope)))
         || ("qualityGate" in parsed && normalizeQualityGate(parsed.qualityGate) === undefined)
         || ("unsupportedModel" in parsed && (typeof parsed.unsupportedModel !== "string" || !["skip","generic"].includes(parsed.unsupportedModel)))) {
        invalidConfig = true
        continue
      }
      data = {...data, ...parsed}
    } catch { invalidConfig = true }
  }
  return {
    behavior: sessionBehaviors.get(sid) ?? (invalidConfig ? "off" : (["auto","preview","off"].includes(data.behavior) ? data.behavior : "auto")),
    scope: ["first","all"].includes(data.scope) ? data.scope : "all",
     qualityGate: normalizeQualityGate(data.qualityGate) ?? "adaptive",
    unsupportedModel: data.unsupportedModel === "generic" ? "generic" : "skip",
  }
}
function hintFor(model:any): string | undefined {
  // Provider names are metadata, not model aliases. Matching them would make a
  // provider named "sol" or "luna" activate the wrong profile.
  const id = `${model?.id ?? ""}`.trim().toLowerCase().replace(/_/g,'-').split('/').at(-1)!.replace(/-latest$/, '')
  for (const [re,h] of hints) if (re.test(id)) return h
  return undefined
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event:any, ctx:any) => {
    const sid = String(ctx.sessionManager?.getSessionId?.() ?? "__default__")
    if (!sessionTurns.has(sid)) sessionTurns.set(sid, 0)
  })
  pi.on("session_end", async (_event:any, ctx:any) => {
    const sid = String(ctx.sessionManager?.getSessionId?.() ?? "__default__")
    sessionBehaviors.delete(sid)
    sessionTurns.delete(sid)
    previewedTurns.delete(sid)
  })

  pi.registerTool({
    name: "prompt_optimizer_preview",
    label: "Prompt preview",
    description: "Show the exact optimized execution prompt for approval in Prompt Optimizer PREVIEW mode. Call once before mutating/external work when PREVIEW is active.",
    parameters: Type.Object({ optimized_prompt: Type.String({ description: "The exact optimized prompt to execute after approval" }) }),
    async execute(_id, params:any, _signal, _update, ctx:any) {
      const sid = String(ctx.sessionManager?.getSessionId?.() ?? "__default__")
      const settings = cfg(ctx)
      const turn = sessionTurns.get(sid) ?? 0
      const hint = hintFor(ctx.model)
      const eligible = settings.behavior === "preview"
        && (settings.scope !== "first" || turn === 1)
      if (!eligible || (!hint && settings.unsupportedModel === 'skip')) {
        return { content:[{type:'text',text:'PREVIEW_REJECTED: this turn is not eligible for Prompt Optimizer PREVIEW.'}], details:{approved:false} }
      }
      if (previewedTurns.get(sid) === turn) {
        return { content:[{type:'text',text:'PREVIEW_REJECTED: this user-turn already has a preview.'}], details:{approved:false} }
      }
      if (!ctx.hasUI) return { content:[{type:'text',text:'PREVIEW_UNAVAILABLE: no interactive UI. Print the optimized prompt and wait for explicit confirmation.'}], details:{approved:false} }
      previewedTurns.set(sid, turn)
      const ok = await ctx.ui.confirm("Prompt preview", params.optimized_prompt)
      if (ok) return { content:[{type:'text',text:`PROMPT_PREVIEW_APPROVED\n${params.optimized_prompt}`}], details:{approved:true,prompt:params.optimized_prompt} }
      const edited = await ctx.ui.editor("Изменить prompt", params.optimized_prompt)
      if (typeof edited === 'string' && edited.trim()) return { content:[{type:'text',text:`PROMPT_PREVIEW_EDITED_AND_APPROVED\n${edited}`}], details:{approved:true,prompt:edited} }
      return { content:[{type:'text',text:'PROMPT_PREVIEW_REJECTED. Do not execute mutating/external work.'}], details:{approved:false} }
    }
  })
  pi.registerCommand("prompt-auto", { description:"Prompt Optimizer: AUTO for this Pi session", handler: async (_a,ctx:any)=>{const sid=String(ctx.sessionManager?.getSessionId?.() ?? "__default__"); sessionBehaviors.set(sid,'auto');ctx.ui.notify('Prompt Optimizer: AUTO','info')} })
  pi.registerCommand("prompt-preview", { description:"Prompt Optimizer: PREVIEW for this Pi session", handler: async (_a,ctx:any)=>{const sid=String(ctx.sessionManager?.getSessionId?.() ?? "__default__"); sessionBehaviors.set(sid,'preview');ctx.ui.notify('Prompt Optimizer: PREVIEW','info')} })
  pi.registerCommand("prompt-off", { description:"Prompt Optimizer: OFF for this Pi session", handler: async (_a,ctx:any)=>{const sid=String(ctx.sessionManager?.getSessionId?.() ?? "__default__"); sessionBehaviors.set(sid,'off');ctx.ui.notify('Prompt Optimizer: OFF','info')} })
  pi.on("before_agent_start", async (event:any, ctx:any) => {
    const settings = cfg(ctx)
    const sid = String(ctx.sessionManager?.getSessionId?.() ?? "__default__")
    if (settings.behavior === 'off') return
    const hint = hintFor(ctx.model)
    if (!hint && settings.unsupportedModel === 'skip') return
    const userTurn = (sessionTurns.get(sid) ?? 0) + 1
    sessionTurns.set(sid, userTurn)
    previewedTurns.delete(sid)
    if (settings.scope === 'first' && userTurn > 1) return
     const gate = gateInstructions(settings.qualityGate)
     const base = gate.base
     const mode = settings.behavior === 'preview' ? PREVIEW : gate.mode
    return { systemPrompt: `${event.systemPrompt}\n\n${base}\n${hint ?? 'Neutral model fallback: use model/provider-neutral shaping only.'}\n${mode}` }
  })
}
