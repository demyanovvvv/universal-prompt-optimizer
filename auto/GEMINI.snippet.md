<!-- prompt-optimizer:auto:start -->
## Prompt Optimizer v5.4
Use the installed `prompt-optimizer` skill as a lean adaptive preflight. When `qualityGate=true`, prefer PASS/LIGHT over FULL when the request is already clear. When `qualityGate=false`, normalize every in-scope request into the leanest model-appropriate execution brief. When the active model is Gemini 3.8 Flash, follow Google's concise/direct prompt guidance and long-context ordering. If PREVIEW is injected by the hook, use `ask_user` to show the exact optimized prompt before changes. AUTO executes silently; OFF skips auto optimization. User instructions override this block.
<!-- prompt-optimizer:auto:end -->
