# GPT-6 conditional prompting guidance

**Provenance:** official GPT-6 family guide, checked 2026-09-23. These recommendations address behavior observed on Astra and are a starting point for Astra, Sol, and Luna; evaluate them on the selected model and workload. Load only when a model profile points here and a condition below matters.

- **Initiative:** treat action requests as authorization to do the in-scope work, not merely acknowledge capability or offer a plan. Complete independently authorized preparation before a genuinely blocking question or approval boundary; do not add hypothetical approval flows or warnings.
- **Instruction conflicts:** make clear that explicit user instructions outrank this optimization layer, subject to higher-priority system/harness requirements. When a skill causes a pause, unfinished work, or a change of direction, identify the exact `SKILL.md`, quote the relevant instruction, and distinguish its requirement from interpretation. Audit relevant skills when requested or when a conflict is observed; do not add a repository-wide audit to every task.
- **Writing style:** state the main point early, use plain language and concise paragraphs, and use lists only when they make parallel or sequential information clearer. Respect requested detail and formatting. Avoid canned transitions, stock phrases, and unprompted “X, not Y” framing.
- **Delegation:** specify when independent work merits subagents only if the harness supports and authorizes them. Follow its delegation policy; do not turn the guide's optional parallel-agent prompt into an unconditional requirement. Keep inter-agent messages readable.
- **Verification:** preserve required checks and use tests appropriate to the change. Avoid implementation-mirroring tests for reversible low-impact edits. After checks pass, broaden or repeat them only for new changes, failures, or unresolved concerns.

Official source: https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices
API features and parameters belong in `harness-openai.md`, not in task prompts.
