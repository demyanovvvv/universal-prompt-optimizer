# Compatibility — v5.16

For practical setup and task examples, see [Usage](USAGE.md) or
[Руководство пользователя](USAGE.ru.md). Adapter-specific instructions are linked below.

| Agent | Shared skills | Exact active model routing | AUTO | PREVIEW | OFF | Mechanism |
|---|---:|---:|---:|---:|---:|---|
| OpenCode | Yes | **Yes** | **Native** | **Advisory native question-tool flow** | **Yes** | v1 chat/system-transform plugin + native TUI plugin + Ctrl+P palette menu |
| Pi | Yes | **Yes** (`ctx.model`) | **Native** | **Native confirm/editor tool** | **Yes** | Pi extension |
| OMP | Yes | **Yes** (`ctx.model`) | **Native** | **Native confirm/editor tool; advisory** | **Yes** | [Oh My Pi extension](adapters/omp/README.md), OMP Zod schemas |
| DeepSeek Harness | Yes | **Yes** (`modelSelection.model`) | **Native** | **Textual; advisory** | **Yes** | [Cordis section provider](adapters/deepseek-harness/README.md), registered Desktop bundle / project CLI overlay |
| Cursor | Yes | **Yes** (`model`/`model_id` hook payload) | Yes | Ask Question / fallback | Yes | beforeSubmitPrompt state bridge + always rule |
| Gemini CLI | Yes | **Exact after BeforeModel observation; explicit configured model before first call when visible** | Yes | **ask_user** / fallback | Yes | BeforeAgent + observation-only BeforeModel hook + GEMINI.md |
| Claude Code | Yes | Claude-family; exact model depends on runtime exposure/config | Yes | native user-question / fallback | Yes | skills + CLAUDE.md |
| GitHub Copilot CLI | Yes | Best effort / explicit override | Yes | interactive question / fallback | Yes | skills + custom instructions |
| OpenAI Codex | Yes | Best effort / explicit override | Yes | interaction-dependent fallback | Yes | skills + AGENTS.md |
| Windsurf | Yes | Best effort / explicit override | Yes | interaction-dependent fallback | Yes | skills + `.windsurf/rules` (project) / global rules |

All ten adapters consume the same 34 model profiles. The November 2026 additions cover Gemini 4 Hydrogen/Carbon, Claude Fable 5.2, GLM-5.3-FlashX, Kimi K3.1 Pro, MiniMax M3.1 Flash and Muse Wonder; Argon and DeepSeek V4.1 Flash guidance is refreshed, with the `-1017` snapshot sharing V4.1 Flash's profile. Exact routing accepts provider-qualified IDs where observable, but does not enable provider access or configure reasoning, sampling, caching, signatures or tool-history serialization. Those host/API requirements are documented separately in profile-linked harness notes. Distinct unregistered variants remain unsupported rather than falling through to a related model.

Fable 5.2 and Hydrogen document signed history/prefix checks that can reject requests when a host rewrites earlier system instructions, tools or messages. Profile selection does not prove provider-transport compatibility: hosts must preserve signed history and use supported instruction-update/compaction mechanisms. This update documents those requirements; it does not modify provider SDKs or claim a real-provider smoke test.

## Important limitations

- OpenCode/OMP/Pi expose the resolved model directly before execution, enabling zero-extra-call native integration. OMP and Pi use distinct host packages and schema APIs; install the matching adapter.
- DeepSeek Harness uses the step's captured `modelSelection.model` and a cooperative prompt section, not a request/history rewrite. Global automatic installation registers a local bundle in the Desktop profile, preserving unrelated manifest fields and patch text; project CLI installation uses an explicit overlay. Native display metadata includes an icon and English/Russian translations selected by Harness. `scope=first` follows the host's durable first turn, including its tool steps; complete-prompt presets suppress cooperative sections. PREVIEW is textual/advisory. The adapter adds no telemetry; Harness's own session-log/telemetry settings remain authoritative.
- Cursor exposes exact `model`/`model_id` in hook input, but `beforeSubmitPrompt` is not a general additional-context injection API. v5 writes a tiny runtime state file; the rule reads it before applying the model profile.
- Gemini CLI `BeforeAgent` provides per-turn context but does not expose the resolved model ID. The adapter therefore registers an observation-only `BeforeModel` hook: it records `llm_request.model` for the session and returns no request override. Before the first model call it uses only explicit `GEMINI_MODEL` / `model.name` when available; otherwise it does not guess. CLI `--model` cannot be known at `BeforeAgent`, so exact first-turn routing is not claimed in that case.
- GitHub Copilot CLI's config-file `userPromptSubmitted` hook cannot rewrite the prompt; GitHub documents `modifiedPrompt` as SDK-programmatic only. v5 uses Agent Skills/custom instructions rather than claiming otherwise.
- For agents without a reliable model-ID hook, “automatic” means use exact runtime identity if the agent exposes it to its own context; otherwise configured profile/neutral fallback. Never guess a materially different variant.
- PREVIEW is advisory for every adapter unless the host itself blocks mutating/external tools until approval. A model instruction to call a question tool is not equivalent to a host-enforced barrier.

- OpenCode v1 session counters and decisions are bounded process-local state. They are
  intentionally not persisted across plugin reloads or OpenCode restarts; status
  output identifies the model match source and PREVIEW enforcement level.

- Windsurf project automation is isolated in `.windsurf/rules/prompt-optimizer.md`; Codex keeps its documented `AGENTS.md` path. The shared AGENTS block explicitly yields to a native Prompt Optimizer adapter when one is active, avoiding a second OpenCode preflight.
