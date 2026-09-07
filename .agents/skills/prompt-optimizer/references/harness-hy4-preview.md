# Hy4-preview harness notes

- Official recommended sampling: `temperature=0.9`, `top_p=1.0` for the documented deployment path.
- Reasoning defaults to `high`, intended for math/coding/reasoning.
- For direct responses, Tencent documents `reasoning_effort: no_think` through chat-template kwargs.
- Do not pair `high` with extra prompt-level “think deeply/double-check repeatedly” scaffolding.

Source: https://huggingface.co/tencent/Hy4-preview
