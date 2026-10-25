# PREVIEW workflow

Read only when behavior is `PREVIEW`.

1. Perform only read-only context gathering needed to resolve the user's references.
   Read-only means no servers, tests/builds, dependency installs, or hooks. In OMP, obey system/session instructions and the repository execution policy; a preview is not approval to edit files or interact with a native UI. If browser context is necessary, load Orca's matched browser guide and use only embedded tabs with explicit page IDs and fresh snapshot refs.
2. Build the exact model-adapted execution prompt.
3. Show it once in the host's native question or confirmation UI when available.
4. Put `Выполнить` first/default and allow edit/custom input when supported.
5. On approval, execute that brief without another preview in the same user-turn.
6. Treat an edited prompt as the source of truth.
7. If no interactive UI exists, print the preview and wait for explicit confirmation. Never pretend approval occurred.

In OMP, use the real `ask` schema when a question is required; do not invent a confirmation tool, option, or approval result. If its UI cannot present the exact brief for approval, show the brief and wait for explicit confirmation. Any later execution retains the host's approval boundaries and Orca browser/computer restrictions.
