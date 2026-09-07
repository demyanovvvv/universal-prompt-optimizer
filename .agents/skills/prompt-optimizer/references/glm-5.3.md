# GLM-5.3 prompt profile

**Provenance:** official Z.ai GLM-5.3 model guidance plus GLM family prompt practices, checked 2026-09-06.

Prefer end-to-end ownership over micromanagement: final goal, relevant context, hard constraints, acceptance criteria, then autonomous investigation/implementation/debugging/verification. Avoid long rigid microstep lists when the model can infer the workflow.

Keep references and output contract explicit. Add a concrete workflow only when the task itself requires ordering or staged approval.

Do not add generic CoT triggers; GLM-5.3 has native reasoning controls.

Official source: https://docs.z.ai/guides/llm/glm-5.3
Runtime: `harness-glm.md`.
