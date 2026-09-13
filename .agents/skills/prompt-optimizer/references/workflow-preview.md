# PREVIEW workflow

Read only when behavior is `PREVIEW`.

1. Perform only read-only context gathering needed to resolve the user's references.
2. Build the exact model-adapted execution prompt.
3. Show it once in the host's native question or confirmation UI when available.
4. Put `Выполнить` first/default and allow edit/custom input when supported.
5. On approval, execute that brief without another preview in the same user-turn.
6. Treat an edited prompt as the source of truth.
7. If no interactive UI exists, print the preview and wait for explicit confirmation. Never pretend approval occurred.
