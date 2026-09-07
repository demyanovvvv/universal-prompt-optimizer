# GLM-5.3-Flash prompt profile

**Provenance:** official Z.ai GLM-5.3-Flash guidance/best practices + GLM family guide, checked 2026-09-06.

Use GLM-5.3 autonomous framing. For visual/multimodal/UI work, add an actual feedback loop when tools permit:

`inspect reference/input → derive requirements → implement → run/render → inspect actual output → compare to reference/criteria → refine → verify`

Map each reference image/file to its role when there are multiple inputs. Judge the rendered result, not just source code. For nonvisual tasks, do not force the visual loop.

Avoid generic CoT triggers.

Official source: https://docs.z.ai/guides/vlm/glm-5.3-flash
Runtime: `harness-glm.md`.
