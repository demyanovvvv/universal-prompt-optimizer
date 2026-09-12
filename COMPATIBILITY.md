# Compatibility — v5.5

| Agent | Shared skills | Exact active model routing | AUTO | PREVIEW | OFF | Mechanism |
|---|---:|---:|---:|---:|---:|---|
| OpenCode | Yes | **Yes** | **Native** | **Advisory native question-tool flow** | **Yes** | v1 chat/system-transform plugin + native TUI plugin |
| Pi | Yes | **Yes** (`ctx.model`) | **Native** | **Native confirm/editor tool** | **Yes** | Pi extension |
| Cursor | Yes | **Yes** (`model`/`model_id` hook payload) | Yes | Ask Question / fallback | Yes | beforeSubmitPrompt state bridge + always rule |
| Gemini CLI | Yes | **Exact after BeforeModel observation; explicit configured model before first call when visible** | Yes | **ask_user** / fallback | Yes | BeforeAgent + observation-only BeforeModel hook + GEMINI.md |
| Claude Code | Yes | Claude-family; exact model depends on runtime exposure/config | Yes | native user-question / fallback | Yes | skills + CLAUDE.md |
| GitHub Copilot CLI | Yes | Best effort / explicit override | Yes | interactive question / fallback | Yes | skills + custom instructions |
| OpenAI Codex | Yes | Best effort / explicit override | Yes | interaction-dependent fallback | Yes | skills + AGENTS.md |
| Windsurf | Yes | Best effort / explicit override | Yes | interaction-dependent fallback | Yes | skills + `.windsurf/rules` (project) / global rules |

## Important limitations

- OpenCode/Pi are the cleanest zero-extra-call integrations because their native extension hooks expose the resolved model directly before execution.
- Cursor exposes exact `model`/`model_id` in hook input, but `beforeSubmitPrompt` is not a general additional-context injection API. v5 writes a tiny runtime state file; the rule reads it before applying the model profile.
- Gemini CLI `BeforeAgent` provides per-turn context but does not expose the resolved model ID. v5.5 therefore registers an observation-only `BeforeModel` hook: it records `llm_request.model` for the session and returns no request override. Before the first model call it uses only explicit `GEMINI_MODEL` / `model.name` when available; otherwise it does not guess. CLI `--model` cannot be known at `BeforeAgent`, so exact first-turn routing is not claimed in that case.
- GitHub Copilot CLI's config-file `userPromptSubmitted` hook cannot rewrite the prompt; GitHub documents `modifiedPrompt` as SDK-programmatic only. v5 uses Agent Skills/custom instructions rather than claiming otherwise.
- For agents without a reliable model-ID hook, “automatic” means use exact runtime identity if the agent exposes it to its own context; otherwise configured profile/neutral fallback. Never guess a materially different variant.
- PREVIEW is advisory for every adapter unless the host itself blocks mutating/external tools until approval. A model instruction to call a question tool is not equivalent to a host-enforced barrier.

- OpenCode v1 session counters and decisions are bounded process-local state. They are
  intentionally not persisted across plugin reloads or OpenCode restarts; status
  output identifies the model match source and PREVIEW enforcement level.

- Windsurf project automation is isolated in `.windsurf/rules/prompt-optimizer.md`; Codex keeps its documented `AGENTS.md` path. The shared AGENTS block explicitly yields to a native Prompt Optimizer adapter when one is active, avoiding a second OpenCode preflight.
