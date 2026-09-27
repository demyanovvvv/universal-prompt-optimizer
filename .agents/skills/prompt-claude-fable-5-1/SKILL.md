---
name: prompt-claude-fable-5-1
description: Force Claude Fable 5.1 prompt optimization. Use when the target model is explicitly Claude Fable 5.1.
metadata:
  version: "5.8"
---
Use the canonical `prompt-optimizer` workflow but force profile `references/claude-fable-5.1.md` plus conditional `references/claude-family.md`. Preserve the user's intent and execute unless prompt-only mode is requested.
