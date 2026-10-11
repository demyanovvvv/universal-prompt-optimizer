# Cursor adapter — v5

For setup, task examples, modes, updates, and removal, see [Usage](../../USAGE.md)
or [Руководство пользователя](../../USAGE.ru.md). This document covers host-specific integration.

Cursor `beforeSubmitPrompt` receives the current `model`, optional structured `model_id`, and `model_params`, but its documented output can block submission rather than inject arbitrary per-prompt context. v5 therefore uses an exact-model state bridge instead of pretending to rewrite the submission hook.

Install:
- `.cursor/hooks/prompt-optimizer-state.py`
- merge `hooks.fragment.json` into `.cursor/hooks.json`
- copy `rules/prompt-optimizer.mdc` into `.cursor/rules/`

The hook writes `.cursor/.prompt-optimizer-runtime.json` for the current generation. The always-applied rule reads that state and selects the matching installed skill profile. PREVIEW uses Cursor's Ask Question/clarification UI when available, otherwise textual confirmation.

This adds no second LLM call; it may add one small runtime-state file read per optimized turn.
