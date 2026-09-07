# Grok 4.6 prompt profile

**Provenance:** official xAI model/reasoning docs, checked 2026-09-06.

Use a direct objective, decisive context, requirements, constraints, evidence/tool policy and acceptance criteria. Let native reasoning handle depth; do not inject `think step by step/use deep reasoning`.

For long tool loops, preserve stable conversation/cache prefixes in the harness and use compaction when appropriate rather than repeatedly restating the same instructions.

Official sources: https://docs.x.ai/developers/grok-4-6 ; https://docs.x.ai/developers/model-capabilities/text/reasoning
Runtime: `harness-grok-4.6.md`.
