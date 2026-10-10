# OpenCode adapter — v5.11

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

Legacy `mode: first|all|off` remains accepted. PREVIEW instructs the active model to use OpenCode's `question` tool with `Выполнить` first/default; if the tool is unavailable it falls back to textual confirmation. No extra optimizer LLM call is made. In OpenCode v1 this remains advisory: the plugin API has no cancellable `tool.execute.before` result or host-level mutation barrier, so a model that ignores the preview instruction cannot be blocked by this adapter alone.

`qualityGate` accepts `adaptive`, `pass`, `light`, `full`, and legacy booleans.
The server stores only bounded, process-local session state and aggregate counters;
entries expire after 30 days and the map is capped at 200 sessions. Prompt text is
hashed for duplicate protection and is not persisted as metrics. A plugin reload or
OpenCode restart starts a new in-memory session store.

The TUI plugin is registered in `tui.json` as:

```json
{"plugin":["./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"]}
```

It exposes `/prompt-optimizer`, `Ctrl+P` → command palette → the
`Prompt Optimizer` group (menu, settings, status), and `Ctrl+Shift+P` as a
shortcut that opens settings directly. The palette menu is structured and shows
the current value of every setting as a subtitle. The compact status chip uses
`● PO AUTO`, `◐ PO PREVIEW`, `○ PO OFF`, `◇ PO GENERIC`, or `! PO CONFIG`; `*` marks a
session override. The settings dialog can save Behavior, Scope, Quality gate,
and Unsupported model to Session, Project, or Global targets. Project settings
are stored in `.opencode/prompt-optimizer.json`, global settings in
`~/.config/opencode/prompt-optimizer.json`, and session settings in the bounded
per-session bridge under `~/.config/opencode/prompt-optimizer-sessions/`; a saved session override remains
active until changed or cleared with `/prompt-optimizer reset`. Session control
commands remain available. `/po-status` opens a native TUI
information dialog with the resolved settings and available model/profile
diagnostics instead of writing the status into the chat. The status output
reports the resolved profile, match source, and that OpenCode v1 PREVIEW is
model-guided rather than a host-enforced execution barrier. The GPT-6 Sol
profile also applies bounded inspection for long repository analysis and must
emit the requested report or an explicit blocking reason once its acceptance
evidence is sufficient.
