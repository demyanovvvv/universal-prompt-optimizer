# Claude family prompt practices — official shared guidance

Source basis: Anthropic “Prompting best practices” for current Claude models, checked 2026-09-06.

Apply these conditionally in addition to the model-specific Claude profile.

- Be clear, direct, and specific about desired outcome and constraints.
- Use examples when output format/tone/structure is hard to describe reliably; keep them relevant and consistent. Anthropic recommends multiple examples for difficult consistency problems, not mandatory few-shot on every prompt.
- Use XML/delimiters when complex prompts mix instructions, long context, examples, and variable inputs. Do not wrap trivial prompts in XML by default.
- Use role/system framing when the role materially improves domain behavior; do not add empty role-play.
- For long-context tasks, place long source material/data high in the prompt and put the specific query/instructions after it. Clearly label multiple documents/sources.
- For evidence-sensitive long-document tasks, ask for grounded evidence/quotes only when the deliverable needs it.
- For code work, inspect relevant existing code/patterns before confidently asserting implementation details.
- Prefer positive output instructions/examples over long negative lists when shaping style.
- Never request hidden chain-of-thought. Use model-native adaptive thinking/effort controls in the harness.

Official source:
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
