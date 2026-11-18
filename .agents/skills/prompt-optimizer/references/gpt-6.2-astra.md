# GPT-6.2 Astra prompt profile

**Provenance:** official GPT-6.2 prompting best practices and Astra model documentation, checked 2026-11-18. The guide presents its prompting patterns as a starting point across GPT-6.2; the behavioral observations below are specifically labeled for Astra and are not assumed for Sol.

GPT-6.2 Astra is positioned for the most demanding tasks. Its documented default writing style is concise and direct. Keep the brief focused on the requested outcome, decisive context, constraints, and completion criteria; specify tone, length, and audience only when they matter.

- If the intended outcome is clear, proceed. When an ambiguity materially changes the result, state a reversible assumption and continue any independent work; ask only for the decision that blocks correctness or authorization.
- For code changes, state relevant repository conventions and behavior existing callers rely on. Prefer the existing abstractions, readable code, narrow scope, and tests required by the task or by a concrete uncovered regression.
- Read `gpt-6.2-family.md` only when a listed conditional behavior matters beyond this concise profile.
- For a requested visual direction, name the desired imagery and typography. Keep interface copy limited to information users need to understand or act.
- For a long task, make the final answer self-contained for a reader who has not seen progress updates.
- Use the conditional GPT-6.2 family guide only when one of these behaviors matters; keep API and runtime settings in `harness-openai.md`.

Official sources:
- https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#prompting-best-practices
- https://developers.openai.com/api/docs/models/gpt-6.2-astra
