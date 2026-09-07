# OpenCode adapter — v5

Strongest integration. OpenCode v2 `context` hook exposes the resolved `{providerID,id,variant}` immediately before dispatch, so the profile is selected from the real active model without relying on provider prefixes.

Config precedence includes project `.opencode/prompt-optimizer.json`, shared project `.prompt-optimizer.json`, global configs and environment overrides.

Recommended:
```json
{"behavior":"auto","scope":"all","unsupportedModel":"skip"}
```

Preview:
```json
{"behavior":"preview","scope":"all","unsupportedModel":"skip"}
```

Off:
```json
{"behavior":"off","scope":"all","unsupportedModel":"skip"}
```

Legacy `mode: first|all|off` remains accepted. PREVIEW instructs the active model to use OpenCode's `question` tool with `Выполнить` first/default; if the tool is unavailable it falls back to textual confirmation. No extra optimizer LLM call is made.
