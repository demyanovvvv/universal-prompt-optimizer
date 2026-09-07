# Muse Spark 1.3 prompt profile

**Provenance:** official Meta AI Research release guidance, checked 2026-09-06.

Describe the work product rather than choreographing tools: why/situation, input artifacts, objective, detailed requirements, output/deliverable, structure, audience and quality bar. Muse is trained to create context from tools across messy/conflicting sources and correct gaps in its plan.

Allow clarification when genuinely ambiguous, user help when truly stuck, and confirmation before consequential actions. If progress-update cadence matters, specify whether to update or work quietly. Preserve long-form constraints without repeating them.

Do not hard-code `max` reasoning availability: Meta said on 2026-09-02 that max reasoning was coming after additional safety testing, so capability-check the current endpoint.

Official source: https://research.meta.ai/blog/introducing-muse-spark-1-3
Runtime: `harness-muse-spark-1.3.md`.
