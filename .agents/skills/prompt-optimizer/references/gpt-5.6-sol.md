# GPT-5.6 Sol prompt profile (legacy versioned profile)

**Provenance:** official GPT-5.6 family guidance; Sol tier positioning is official. Checked 2026-09-06.

- Favor lean prompts: state each instruction once; remove repetition, redundant examples, and bloated tool descriptions.
- Rely on improved intent understanding instead of prescribing every step; retain domain context, hard constraints, approval boundaries, and success criteria.
- Define autonomy once: inspect/review vs change/build/fix; permit safe in-scope local work and proportionate validation; confirm external/destructive/costly/material scope expansion.
- Expose only task-relevant tools and describe them precisely.
- Keep examples/style guidance only when they encode a real product/output requirement or fix a measured gap.
- Calibrate response length explicitly only when needed; avoid generic verbosity instructions that make the result too short.
- Sol is the flagship GPT-5.6 tier: preserve full task fidelity rather than compressing away decisive context.

Official source: https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6
Runtime settings: `harness-openai.md`.
