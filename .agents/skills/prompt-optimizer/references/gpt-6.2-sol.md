# GPT-6.2 Sol prompt profile

**Provenance:** official GPT-6.2 family prompting best practices and Sol model documentation, checked 2026-11-18. OpenAI describes Sol as its go-to model for everyday work, coding, and agents at scale. The family guide offers a starting point for both Astra and Sol, but its detailed behavioral observations are not evidence of a Sol-only tendency.

Use a direct brief with the requested outcome, relevant context, constraints, and expected result. For coding, include the project conventions and existing behavior that the change must preserve. State a preferred audience, tone, or visual direction only when it affects the deliverable. Evaluate these family-level patterns on Sol and the intended workload instead of importing GPT-6 or GPT-6.1 tier assumptions.

- When intent is clear, let the model complete the authorized task. For consequential ambiguity, ask only for the missing decision; state reversible assumptions when that keeps independent work moving.
- For a long task, make the final answer self-contained for someone who did not follow intermediate updates.
- Read `gpt-6.2-family.md` only when its task-completion, coding, writing, or visual guidance adds value beyond this profile.
- Keep API and runtime settings in `harness-openai.md`, not in prompt text.

Official sources:
- https://developers.openai.com/api/docs/guides/latest-model/gpt-6.2-astra#prompting-best-practices
- https://developers.openai.com/api/docs/models/gpt-6.2-sol
