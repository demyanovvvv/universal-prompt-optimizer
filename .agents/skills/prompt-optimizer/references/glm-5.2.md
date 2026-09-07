# GLM-5.2 prompt profile

**Provenance:** official Z.ai/BigModel GLM-5.2 + GLM prompt/coding guides, checked 2026-09-06.

For substantial engineering/refactor work, make the current architecture/dependencies/interfaces and affected scope explicit or instruct the agent to inspect them first. A short execution/validation plan is useful when multiple modules/contracts are involved. Then implement completely and verify with the task-relevant build/lint/tests/runtime checks.

State non-negotiable interface/dependency constraints and observable done criteria. Provide source/reference materials when fidelity matters. Use delimiters/examples/structured output only when they solve a format/context problem.

Do not expose hidden reasoning; translate “step-by-step” needs into observable stages and validation.

Official sources: https://docs.bigmodel.cn/cn/guide/models/text/glm-5.2 ; https://docs.bigmodel.cn/cn/guide/platform/prompt
Runtime: `harness-glm.md`.
