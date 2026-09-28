# Windsurf adapter — v5

Windsurf/Cascade can consume the shared `.agents/skills/` tree and repository/global rules. v5 uses the shared adaptive preflight rather than claiming a prompt-replacement hook that the package cannot guarantee across Windsurf versions.

When Cascade exposes an exact selected model to the agent, apply the matching profile; otherwise use an explicit override or neutral fallback. AUTO/PREVIEW/OFF semantics are the same as the core skill. PREVIEW uses the available user-question/confirmation interaction when supported, otherwise textual confirmation.

## v5.10 installer

Project installs now use a dedicated always-on workspace rule at `.windsurf/rules/prompt-optimizer.md` rather than sharing the repository-root `AGENTS.md`. This prevents cross-agent rule collisions when OpenCode/Codex/Windsurf are installed together. Global installs continue to use `~/.codeium/windsurf/memories/global_rules.md`.
