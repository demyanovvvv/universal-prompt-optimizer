---
name: prompt-kimi-k3
description: Optimize the user's raw task specifically for Kimi K3, then execute it. Use when the user explicitly selects this model profile.
compatibility: Agent Skills compatible coding agents
metadata:
  version: "5.5"
---

Apply target profile `kimi-k3`.

Activate the canonical `prompt-optimizer` skill if the harness supports skill activation. Otherwise read `../prompt-optimizer/SKILL.md` and the matching reference profile, then apply the same workflow directly.

Treat the current user request as the raw task. Optimize internally and execute unless the user explicitly asks for prompt-only output. Preserve exact intent and constraints; do not expose the internal execution brief unless asked.
