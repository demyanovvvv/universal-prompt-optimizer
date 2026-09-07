# Migration v4 → v5

1. Install v5 over the same scope; backups are created unless `--no-backup` is passed.
2. v4 OpenCode `mode: first|all|off` remains readable, but v5 prefers independent fields `behavior: auto|preview|off` and `scope: first|all`.
3. v5 default changes from first-turn-only to `behavior=auto`, `scope=all` because the quality gate prevents needless rewriting of simple follow-ups.
4. Add the new `prompt-claude-fable-5-1` profile/command.
5. If you use Cursor, install the new hook state bridge plus rule.
6. If you use Pi, replace the old always-on preflight extension with the v5 extension for exact model routing and native preview.
7. Gemini CLI keeps BeforeAgent integration, now behavior-aware and preview-capable via `ask_user`.
