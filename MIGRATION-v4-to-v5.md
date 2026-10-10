# Migration v4 → v5

1. Install v5 over the same scope; backups are created unless `--no-backup` is passed.
2. v4 OpenCode `mode: first|all|off` remains readable, but v5 prefers independent fields `behavior: auto|preview|off` and `scope: first|all`.
3. v5 default changes from first-turn-only to `behavior=auto`, `scope=all` because the quality gate prevents needless rewriting of simple follow-ups.
4. From v5.9 onward, OpenCode installs only the universal `/prompt`, `/prompt-only`, and `/prompt-optimizer` command files. Reinstall in the same scope to remove stock legacy model commands, including the older Opus/Fable `Optimize and execute with…` templates. Commands with custom instructions and third-party commands are preserved; model profiles are selected internally from the active model. Restart OpenCode to refresh the installed command list.
5. If you use Cursor, install the new hook state bridge plus rule.
6. If you use Pi, replace the old always-on preflight extension with the v5 extension for exact model routing and native preview.
7. Gemini CLI keeps BeforeAgent integration, now behavior-aware and preview-capable via `ask_user`.
