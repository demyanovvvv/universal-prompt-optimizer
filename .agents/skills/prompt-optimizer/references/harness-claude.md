# Claude harness notes

Prompt shaping and Claude runtime state are separate.

- Keep adaptive thinking/effort in runtime; do not simulate it with `think step by step`.
- **Fable 5.1:** adaptive thinking is always on; default effort is `high`, but Anthropic recommends testing all effort levels on representative workloads. Keep conversation history append-only and return assistant turns/thinking blocks exactly as the API produced them where binding rules apply. Do not rewrite earlier prefixes between turns merely to inject temporary reminders; use the supported turn-scoped/mid-conversation mechanisms. When user-facing progress is desired, configure thinking display/progress handling rather than asking for hidden reasoning. Leave enough output room at xhigh/max.
- **Fable 5:** use native adaptive thinking/effort; do not request summarized/private reasoning extraction. For long asynchronous agents, progress delivery and fresh-context verifier orchestration are harness concerns when implemented.
- **Opus 5:** thinking is on by default; lower effort for latency/cost before disabling where possible. Do not use effort as output-length control.
- **Opus 4.8:** enable adaptive thinking explicitly for intelligence-sensitive coding where your API integration requires it; high/xhigh are runtime choices, not prompt phrases.
- **Sonnet 5:** adaptive thinking is on by default. Remove unsupported/non-default sampling parameters documented for the model; steer style in prompt instead.

Sources:
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
