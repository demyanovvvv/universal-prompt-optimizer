# GLM-5.3-FlashX prompt profile

**Provenance:** official Z.ai GLM-5.3-Flash/FlashX model page and GLM family best practices, checked 2026-11-13. FlashX is a separate model code/speed tier, not an alias for GLM-5.3-Flash. The separately listed `glm-5.3-flashx-legal` variant is not covered or inferred by this profile; no behavioural-equivalence statement was found in the checked sources.

For complex tasks, use Z.ai's Goal / Context / Constraints / Done when framing where it adds missing information, and plan only when complexity warrants it. Preserve precise short requests unchanged. Z.ai's guidance on project configuration and compact, checkable memory rules is family-level advice, not authorization to rewrite project files or trim existing constraints.

For visual, UI, Office-document, rendering or CAD work, state the deliverable and require a feedback loop against rendered output — `implement → render/run → inspect actual output → compare to criteria → refine → verify` — and have the result state what was verified and what risks remain. That is the shared shape of Z.ai's published recipes; do not force the visual loop onto non-visual tasks, and do not invent a FlashX-specific prompt template.

Native thinking cannot be disabled on this model. Never request hidden chain-of-thought or a visible reasoning plan; preserved/interleaved thinking and `reasoning_effort` are harness concerns (`harness-glm.md`).

Official sources:
- Model page (GLM-5.3-Flash/FlashX): https://docs.z.ai/guides/vlm/glm-5.3-flash
- Best practices: https://docs.z.ai/devpack/resources/best-practice
- Memory mechanism: https://docs.z.ai/devpack/resources/memory-mechanism

Runtime: `harness-glm.md`.
