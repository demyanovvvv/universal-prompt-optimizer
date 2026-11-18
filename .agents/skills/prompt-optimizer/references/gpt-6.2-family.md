# GPT-6.2 conditional prompting guidance

**Provenance:** official GPT-6.2 family prompting best practices, checked 2026-11-18. OpenAI presents the patterns below as a starting point across GPT-6.2 and says the examples address behaviors seen with Astra and Sol. The guide labels its behavior overview as Astra-specific; do not present those observations as Sol-specific measurements. Load only when a relevant behavior needs prompt tuning.

- **Task completion:** define the intended outcome and decisions needing user input. Allow reasonable, reversible assumptions and continued authorized work when details are unclear; ask only about a material blocker.
- **Coding:** provide the repository conventions and caller behavior that matter. Prefer existing logic, narrow scope, readable implementation, and tests for the task or a concrete uncovered regression.
- **Writing:** specify audience, tone, and length when they affect the result. For external material, include enough context for its intended reader; when revising text, preserve wording outside the requested edits.
- **Long tasks:** make the final response self-contained rather than relying on progress updates or internal shorthand.
- **Frontend:** name a required visual style, imagery, and typography when the product needs them. Keep interface text focused on what users need to know or do.

These are prompt-shaping recommendations, not reasoning-effort, sampling, API, tool-history, or caching settings. The guidance is not a measured quality claim for either model or workload.

Official source: https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#prompting-best-practices
