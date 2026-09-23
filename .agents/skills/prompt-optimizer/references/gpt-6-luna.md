# GPT-6 Luna prompt profile

**Provenance:** official GPT-6 family prompting guidance and official Luna positioning (efficient, repeatable work at scale), checked 2026-09-23. The guide describes behavior observed on Astra and recommends these prompts as a starting point across GPT-6; validate them on Luna and the chosen workload. The compact bounded-brief preference below is a derived operational heuristic, not a measured Luna-specific prompting rule.

## Preferred shaping
- Use a compact bounded brief: one clear outcome, decisive inputs, hard constraints, exact output schema when requested, and observable done criteria.
- Remove repetition, generic role-play, nonessential examples, and tool narration while preserving correctness-critical context and required verification.
- For authorized work, infer routine intent and follow through to completion; preserve plan-only and read-only requests. Ask only when a missing decision materially changes the outcome, continuing independent authorized work where possible.
- Read `gpt-6-family.md` only when skill conflicts, writing style, delegation, or testing behavior needs tuning. Add only the relevant guidance once.

## Avoid
- Treating efficiency as permission to return a partial result, omit constraints, or skip required checks.
- Importing GPT-5.6 guidance as Luna-specific evidence or adding “think harder/step by step” scaffolding.

Official source: https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
Runtime settings: `harness-openai.md`.
