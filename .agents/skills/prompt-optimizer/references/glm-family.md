# GLM family prompt practices — official shared guidance

Source basis: Z.ai / BigModel prompt-engineering and coding-prompt guides, checked 2026-09-06.

Apply conditionally:

- Make instructions precise and specific; include decisive background/context.
- Use system instructions/role framing when a stable role/style/task policy materially helps.
- Use clear delimiters between instructions, input data, references, and examples when mixed content could be confused.
- Use few-shot examples when exact style/format/pattern consistency matters.
- Provide reference materials instead of expecting factual recall when source fidelity matters.
- Specify output length/format when it is a real requirement; use structured JSON when downstream parsing requires it.
- For complex tasks, decompose into meaningful stages/subproblems when that improves execution, but do not expose or demand private chain-of-thought. Prefer an observable workflow/plan, actions, and verification.
- For coding, tell the model what/why/constraints; inspect the existing project/architecture first when the task depends on current code; use errors/test feedback to iteratively correct implementation.

Official sources:
https://docs.bigmodel.cn/cn/guide/platform/prompt
https://docs.bigmodel.cn/cn/guide/coding/prompt
