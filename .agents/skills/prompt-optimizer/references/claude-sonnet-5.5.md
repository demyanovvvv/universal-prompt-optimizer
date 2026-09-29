# Claude Sonnet 5.5 prompt profile

**Provenance:** official Anthropic Sonnet 5.5 prompting guide and shared Claude prompting best practices, checked 2026-09-29.

Use a direct task brief with the objective, relevant context, exact scope, constraints, deliverable, and observable completion criteria. Existing Sonnet 5 prompts remain a useful baseline, but tune the execution brief to the workload:

- For agentic coding and multi-step tool use, state the scope boundary, when to continue independently, when to ask, and what verification must happen before reporting completion. Prevent both premature check-ins and unauthorized expansion.
- Use examples only when the required output shape, tone, or consistency is difficult to specify directly. Use XML/delimiters for genuinely mixed instructions, context, examples, or variable inputs; do not wrap simple prompts in ceremony.
- For long-context work, put source material before the final query and label multiple documents. Ask for grounded evidence or quotations only when the deliverable needs them.
- For JSON or other structured output, state the exact schema and keep the task instructions separate from the data. Do not rely on a prefilled response to force formatting.
- For tool use, make tool-selection and completion conditions explicit, batch independent calls when the harness allows it, and keep user-facing progress useful rather than narrating every action.
- For coding, require inspection of relevant existing patterns and verification of the changed behavior. Report what was completed, verified, and not confirmed.
- Avoid generic “think harder”, hidden-CoT requests, rigid manual reasoning steps, and blanket high-effort instructions. Effort, thinking mode, and token limits belong to runtime configuration and should be calibrated against the workload.
- Keep research and file creation bounded. Prefer targeted edits, avoid optimizing only to pass tests or hardcoding around failures, and stop when the requested outcome and checks are satisfied.

Official sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
Runtime: `harness-claude.md`.
