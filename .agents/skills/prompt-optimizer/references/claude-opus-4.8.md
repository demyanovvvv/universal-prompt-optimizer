# Claude Opus 4.8 prompt profile

**Provenance:** official Anthropic model-specific guide + shared Claude best practices, checked 2026-09-06.

Be literal and explicit about affected scope: if a rule applies to every component/route/state/variant/breakpoint, say so rather than expecting automatic propagation. If direct evidence can be obtained with tools, explicitly authorize/require the relevant tool use when needed; Opus 4.8 may otherwise keep reasoning instead of checking.

For frontend/design, replace vague “modern/beautiful” instructions with concrete visual direction: palette, typography, spacing, radius, layout, surfaces, motion, and reference-derived constraints. Positive examples can steer output style better than long negative lists.

For code review, preserve the user's reporting threshold; otherwise describe concrete reportable failures (incorrect behavior, test failure, violated requirement) rather than an ambiguous “only important bugs” filter that literal interpretation may over-apply.

Do not encode adaptive-thinking/effort configuration in prompt text.

Official source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8
Runtime: `harness-claude.md`.
Shared guidance (conditional): `claude-family.md`.
