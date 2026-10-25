# OMP native extension

The `omp` adapter targets `@oh-my-pi/pi-coding-agent`. It uses the host's injected `pi.zod` schema builder, not Pi's TypeBox dependency. Install with `python install.py --agents omp --auto --scope project --yes` (Windows: `py -3` instead of `python`); use `--scope global` for the current user. Restart OMP after installation. Project discovery uses `.omp/extensions/prompt-optimizer/index.ts`; global discovery uses `~/.omp/agent/extensions/prompt-optimizer/index.ts`. The deployed extension is self-contained with `index.ts`, runtime, and exact model registry.

The extension appends model-aware shaping instructions to the existing system prompt. It never replaces the user's task, changes thinking/runtime settings, or grants tool approvals. AUTO executes with shaping; OFF adds no shaping. `/prompt-optimizer auto|preview|off|status` changes only process-local session behavior. Configuration is read from `~/.config/prompt-optimizer/config.json` and the project `.prompt-optimizer.json`; malformed configuration fails closed to OFF even when a session override exists. Unsupported models default to skip; explicit `unsupportedModel: "generic"` enables neutral shaping. Provider names do not select model profiles.

`scope: "first"` means the first submitted agent-start turn in the extension session, including turns skipped because the model is unsupported or behavior is OFF. Factory-local state prevents OMP child sessions from inheriting another factory's overrides or counters. Shutdown clears state and session tracking is bounded.

## PREVIEW boundary

PREVIEW asks the model to call `prompt_optimizer_preview` before mutating or external work. The tool displays the exact proposed prompt for confirmation; declining opens an editor, and submitting non-empty edited text approves that text. Cancelling the editor rejects execution. A turn receives at most one interactive preview. Without an interactive UI, the tool returns an unavailable result instructing the model to print the prompt and wait for explicit confirmation.

This is a model-mediated workflow, **not a mandatory tool-execution sandbox**: the extension does not classify or intercept every mutating/external tool, cancel the agent loop, or enforce that subsequent work follows the approved text. Existing OMP approval boundaries remain authoritative. `hasUI` does not guarantee every RPC/ACP client implements confirmation or editor dialogs; unavailable dialogs cannot provide approval.

## Privacy and maintenance

No extra LLM request, network client, telemetry, or raw-prompt filesystem persistence is added. Preview text travels through the normal host tool result and may therefore appear in ordinary session history. Session bookkeeping stores only IDs, counters, and behavior overrides.

The Pi adapter contains the canonical shared runtime. OMP carries a generated, self-contained copy for deployment; regenerate/check it together with model-registry outputs. Runtime behavior coverage lives in `tests/omp-runtime.test.ts`; run `npm run verify:ts`, `npm run test:runtime`, and `npm run check:model-registry` after integration.
