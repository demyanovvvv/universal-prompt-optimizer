# Gemini 3.8 Flash prompt profile

**Provenance:** official Google Gemini 3 / Gemini 3.8 Flash developer guidance, checked 2026-09-06.

Be concise, direct and clear. Gemini 3 may over-analyze verbose/overly complex legacy prompt-engineering frameworks, so do not expand a good short request into a large ritual template. Prefer PASS/LIGHT aggressively.

When using large datasets/codebases/books/videos, put the long data/context first and the specific instruction/question at the end; anchor with “Based on the preceding information…” when useful. Explicitly steer output verbosity/persona only when needed.

Do not inject old CoT scaffolding. Reasoning level belongs to runtime; 3.8 Flash is designed to reason/tool/verify iteratively at medium/high when needed.

Official sources: https://ai.google.dev/gemini-api/docs/generate-content/gemini-3 ; https://ai.google.dev/gemini-api/docs/latest-model
Runtime: `harness-gemini-3.8-flash.md`.
