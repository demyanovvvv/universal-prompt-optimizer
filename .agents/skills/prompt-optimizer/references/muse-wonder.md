# Meta Muse Wonder prompt profile

**Provenance:** official Meta Model API model page, reasoning, tool-calling, structured-output and computer-use documentation plus the Muse Wonder model card (2026-10-12); checked 2026-11-13. The Model API ID is `muse-wonder-1.0`; the requested `meta/muse-wonder` is an optimizer routing alias. No dedicated Wonder prompting guide was found in the checked sources, so the task/deliverable guidance below is an explicit optimizer heuristic, not vendor instruction. Muse Wonder Full is a different variant with no Model API ID and is not covered by this profile.

Describe the work product rather than choreographing tools: situation, input artifacts, objective, requirements, deliverable shape, audience or quality bar, and the hard constraints that must hold. Meta documents detailed instruction following; the lean deliverable-focused shape is an optimizer heuristic. Do not borrow Muse Spark Open guidance (recipient channels, reasoning-strength integers, system-prompt ordering) or assume Spark-specific API behavior for Wonder.

State what "done" looks like and what must be verified, then let the model plan, parallelize tools and recover from errors on its own.

- The model is trained to ask when a request is genuinely ambiguous and to check in before important actions. Say explicitly whether to proceed without asking and which actions need sign-off, especially where tools can take irreversible actions. Preserve the host's and user's existing approval boundaries unchanged.
- Reasoning is private and controlled by runtime `reasoning_effort`. Never ask for chain-of-thought, "show your reasoning", or step-by-step thinking; ask for a reasoning summary only through the Responses API when a summary is actually wanted, and treat it as optional.
- For a contractual machine-readable output, preserve the requested schema exactly. Native JSON-schema enforcement and recursive-schema limitations are endpoint capabilities in the harness notes, not permission to silently flatten a user's schema.
- For image, video or PDF inputs, state what to extract or compare. For computer use, specify the goal, stopping condition and actual safety boundaries; do not invent a step budget or tools. Media serialization, coordinates, screenshots and safety acknowledgements belong to the host.
- Keep goal, constraints and prior decisions available in context for long-running work, and specify a progress cadence only if a human is actually watching.
- Do not promise Muse Wonder Full behavior, and treat preview status and the documented visual/spatial (especially 3D) limitations as real.

Reasoning continuity across turns and endpoint selection are harness concerns (`harness-muse-wonder.md`).

Official sources:
- Model page: https://dev.meta.ai/docs/muse-wonder
- Reasoning: https://dev.meta.ai/docs/reasoning.md
- Tool calling: https://dev.meta.ai/docs/tool-calling.md
- Structured output: https://dev.meta.ai/docs/structured-output.md
- Computer use: https://dev.meta.ai/docs/computer-use.md
- Model card: https://research.meta.ai/static/muse-wonder-model-card/

Runtime: `harness-muse-wonder.md`.
