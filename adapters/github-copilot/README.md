# GitHub Copilot CLI adapter — v5

For setup, task examples, modes, updates, and removal, see [Usage](../../USAGE.md)
or [Руководство пользователя](../../USAGE.ru.md). This document covers host-specific integration.

Copilot CLI supports Agent Skills from `.agents/skills`, custom instructions and hooks. Command/config-file `userPromptSubmitted` hook output does **not** rewrite the prompt; GitHub documents `modifiedPrompt` as SDK-programmatic only. Therefore v5 does not pretend the static CLI hook transparently replaces user text.

The canonical skill + `.github/copilot-instructions.md` provide the adaptive zero-extra-call preflight. Exact cross-model routing, including GPT-6.1 Sol and Claude Sonnet 5.5, is used only when the active model is unambiguously available to the agent; otherwise explicit profile override or neutral fallback is used.

In PREVIEW, use Copilot's interactive user-question capability when available; if the session is non-interactive or user questions are disabled, show the prompt and wait for explicit confirmation. AUTO executes silently; OFF skips auto preflight.
