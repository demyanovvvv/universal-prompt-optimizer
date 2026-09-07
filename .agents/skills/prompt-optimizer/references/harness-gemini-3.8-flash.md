# Gemini 3.8 Flash harness notes

- `thinking_level`: `low`, `medium`, `high`; default `medium`. Google recommends medium for most tasks including complex coding/agentic use, high for the hardest reasoning/multi-step work.
- `minimal` is not supported by Gemini 3.8 Flash.
- Prefer Gemini 3.x thinking-level controls over legacy thinking budgets/CoT prompt hacks.
- Follow current migration guidance for generation parameters; avoid carrying older temperature/top_p/top_k tuning forward unless the current endpoint explicitly documents it.

Sources:
https://ai.google.dev/gemini-api/docs/latest-model
https://ai.google.dev/gemini-api/docs/generate-content/gemini-3
