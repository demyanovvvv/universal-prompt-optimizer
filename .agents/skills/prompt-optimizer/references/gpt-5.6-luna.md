# GPT-5.6 Luna prompt profile

**Provenance:** official GPT-5.6 family guidance + official Luna positioning (efficient/high-volume). The strongest prompt-compression bias here is an operational heuristic. Checked 2026-09-06.

- Use the leanest bounded brief that preserves correctness: one clear outcome, decisive context only, hard constraints, output shape if needed, and observable done criteria.
- Remove repetition, generic role-play, nonessential examples and unnecessary tool narration.
- Define autonomy/approval boundaries once; keep validation efficient and task-proportionate.
- Do not compensate for model tier with long “think harder/step by step” text.

Official sources: https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6 and https://developers.openai.com/api/docs/models
Runtime settings: `harness-openai.md`.
