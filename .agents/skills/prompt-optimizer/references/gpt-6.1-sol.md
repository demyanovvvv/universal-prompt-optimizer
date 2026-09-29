# GPT-6.1 Sol prompt profile

**Provenance:** official OpenAI GPT-6 guide and GPT-6.1 Sol model documentation, checked 2026-09-29. Family prompting advice is a starting point; evaluate it on this model and the intended workload.

GPT-6.1 Sol balances speed, cost, and intelligence with near-Astra performance for complex coding, computer use, and professional work. Keep a lean brief with the outcome, decisive context, scope, hard constraints, approval boundaries, and observable completion criteria.

- For authorized implementation or bugfix work, follow through on in-scope changes and relevant verification; ask only when a missing decision materially changes the result.
- For repository analysis, gather bounded current evidence rather than expanding into unrelated files or relying on stale documentation; stop once enough evidence supports the requested answer.
- Put precise output requirements and correctness-critical checks in the task when needed, without micro-managing reasoning steps or adding generic “think harder” scaffolding.
- Keep the legacy `gpt-6-sol` / `sol` routing separate; do not assume the model ID or runtime behavior is interchangeable. `reasoning.effort` is a runtime setting, not prompt text.

Official sources:
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
Runtime settings: `harness-openai.md`.
