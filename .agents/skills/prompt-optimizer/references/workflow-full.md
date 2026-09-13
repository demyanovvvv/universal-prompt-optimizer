# FULL workflow

Read only after the quality gate selects `FULL`.

Build a concise execution brief from the user's request and relevant context. Select only useful fields: objective, decisive context, requirements, affected scope and preserved behavior, hard constraints, inputs/references, autonomy or approval boundaries, success criteria, verification, and output.

Use task-specific detail only when it changes execution:

- coding or bugfix: actual repository state, affected interfaces, root-cause evidence, and relevant validation;
- refactor or migration: contracts, dependencies, compatibility, rollout, and regression checks;
- agentic or long-horizon: outcome, safe autonomy, completion boundary, and stop condition without micromanagement;
- frontend or multimodal: map references to concrete visual, responsive, state, and rendered-behavior requirements;
- research or fresh facts: source quality, freshness, evidence, and requested citations;
- artifact or document: audience, fidelity, required content, structure, and output artifact.

Use examples, delimiters, role framing, structured output, decomposition, or explicit style only when that technique solves a concrete problem. Do not expose private reasoning.

For coding work, end with a concise factual result: changes made, validation actually run and its result, and any concrete blocker or unverified boundary. For research, distinguish confirmed evidence from inference and cite sources when requested. Do not add a report template where the requested output does not need one.
