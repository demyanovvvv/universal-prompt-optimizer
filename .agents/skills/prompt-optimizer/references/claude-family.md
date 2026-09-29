# Claude family prompt practices — official shared guidance

Source basis: Anthropic “Prompting best practices” for current Claude models, checked 2026-09-29.
Claude Code implementation practices checked 2026-09-23; apply them only in an agentic coding environment that supports the relevant tools.

Apply these conditionally in addition to the model-specific Claude profile.

- Be clear, direct, and specific about desired outcome and constraints.
- State when the model should continue independently, when it should ask, and what observable condition ends the task; keep autonomy bounded by the requested scope.
- Use examples when output format/tone/structure is hard to describe reliably; keep them relevant and consistent. Anthropic recommends multiple examples for difficult consistency problems, not mandatory few-shot on every prompt.
- Use XML/delimiters when complex prompts mix instructions, long context, examples, and variable inputs. Do not wrap trivial prompts in XML by default.
- Use role/system framing when the role materially improves domain behavior; do not add empty role-play.
- For long-context tasks, place long source material/data high in the prompt and put the specific query/instructions after it. Clearly label multiple documents/sources.
- For evidence-sensitive long-document tasks, ask for grounded evidence/quotes only when the deliverable needs it.
- For code work, inspect relevant existing code/patterns before confidently asserting implementation details.
- Give implementation work an observable completion check when one is available; report evidence and distinguish completed, verified, and unconfirmed work.
- For tool use, describe the tool-selection or completion condition when it matters, batch independent calls when supported, and use progress updates only when they help the user follow a long run.
- Keep context bounded: target relevant files and dependencies first, preserve exact decisions and constraints across long runs, and use a plan only when uncertainty or scope warrants it.
- For review, use concrete correctness criteria such as incorrect behavior, failed tests, violated requirements, or misleading results; avoid vague severity filters that hide findings.
- Prefer positive output instructions/examples over long negative lists when shaping style.
- Avoid optimizing only for passing tests: preserve the requested behavior, inspect the relevant implementation, and do not hardcode around failures.
- Never request hidden chain-of-thought. Use model-native adaptive thinking/effort controls in the harness.

Official source:
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
https://code.claude.com/docs/en/best-practices
