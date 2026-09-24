# OpenCode adapter — v5.6

Strongest integration. The server plugin uses OpenCode v1 `chat.message` and
`experimental.chat.system.transform` hooks, so the profile is selected from the
resolved model immediately before dispatch without relying on provider prefixes.
The plugin also keeps a separate native TUI target for compact status and
on-demand controls.

Config precedence includes project `.opencode/prompt-optimizer.json`, shared project `.prompt-optimizer.json`, global configs and environment overrides.

Recommended:
```json
{"schemaVersion":1,"behavior":"auto","scope":"all","qualityGate":"adaptive","unsupportedModel":"skip"}
```

Preview:
```json
{"schemaVersion":1,"behavior":"preview","scope":"all","qualityGate":"adaptive","unsupportedModel":"skip"}
```

Off:
```json
{"schemaVersion":1,"behavior":"off","scope":"all","qualityGate":"adaptive","unsupportedModel":"skip"}
```

Legacy `mode: first|all|off` remains accepted. PREVIEW instructs the active model to use OpenCode's `question` tool with `Выполнить` first/default; if the tool is unavailable it falls back to textual confirmation. No extra optimizer LLM call is made.

`qualityGate` accepts `adaptive`, `pass`, `light`, `full`, and legacy booleans.
The server stores only bounded, process-local session state and aggregate counters;
entries expire after 30 days and the map is capped at 200 sessions. Prompt text is
hashed for duplicate protection and is not persisted as metrics. A plugin reload or
OpenCode restart starts a new in-memory session store.

The TUI plugin is registered in `tui.json` as:

```json
{"plugin":["./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"]}
```

It exposes `/prompt-optimizer`, `/po-status`, and `Ctrl+Shift+P`. Session control
commands are ephemeral and do not rewrite JSON configuration. The status output
reports the resolved profile, match source, and that OpenCode v1 PREVIEW is
model-guided rather than a host-enforced execution barrier.
