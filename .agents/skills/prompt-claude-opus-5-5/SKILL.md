---
name: prompt-claude-opus-5-5
description: Optimize the user's raw task specifically for Claude Opus 5.5, then execute it. Use when the user explicitly selects this model profile.
compatibility: Agent Skills compatible coding agents
metadata:
  version: "5.8"
---

Apply target profile `claude-opus-5.5`.

Activate the canonical `prompt-optimizer` skill if the harness supports skill activation. Otherwise read `../prompt-optimizer/SKILL.md`, `../prompt-optimizer/references/claude-opus-5.5.md`, and conditionally relevant `../prompt-optimizer/references/claude-family.md`, then apply the same workflow directly.

Treat the current user request as the raw task. Optimize internally and execute unless the user explicitly asks for prompt-only output. Preserve exact intent, constraints, required verification, and approval boundaries; do not expose the internal execution brief unless asked.
