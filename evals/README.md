# v5 evaluation matrix

Run each representative case with: (1) optimizer OFF, (2) AUTO, (3) PREVIEW when interaction is supported, and (4) explicit model override for router sanity.

Measure **task-level** efficiency, not just first-prompt length:
- first-pass success;
- preserved explicit requirements/literals;
- invented-requirement rate;
- scope drift/unrelated changes;
- unnecessary clarification/approval pauses;
- required-check completion;
- supplemental over-verification;
- total input + reasoning + output tokens per completed task;
- tool calls, latency, retries, and user interventions.

Quality gates must be tested explicitly: PASS must leave an already-good prompt essentially unchanged; LIGHT may add only missing high-value structure; FULL is reserved for genuinely complex/ambiguous work. PREVIEW must never execute before approval and must not preview twice in the same turn.

For GPT-6 Astra, also measure whether adaptive PASS adds zero optimizer context, authorized implementation continues through its observable completion boundary, safe local work avoids needless approval, explicit plan-only boundaries stop mutation, and skill guidance is loaded only for skill-related work.

Developer guidance is a constraint on the optimizer, not an excuse to override the user's/project's explicit rules.

## Deterministic CI check

```bash
python -B evals/run.py
python -B evals/run.py --output evals/results/latest.json
python -B evals/run.py --strict-coverage
npm run test:evals:strict
```

The runner validates the fixture schema, model registry membership, unique IDs,
and required adversarial cases without making provider calls. It is not a
substitute for measured OFF/AUTO/PREVIEW runs; it provides a stable contract that
a future provider runner can consume without changing `cases.jsonl`. The result also
contains `coverage`, which reports how many executable contracts declare each field
and value. Coverage is fixture coverage, not a quality score.
Reports also include `caseResults`, one stable entry per fixture with its `id`,
pass/fail status, and validation errors. A provider runner can use these IDs to
join measured OFF/AUTO/PREVIEW outcomes without changing the fixture schema.
Malformed contract values are reported as validation errors; profile values must
come from the model registry and task types must match the runtime classifier.
Invalid JSON, non-object JSONL lines, and unreadable fixture files also return the
same schema-versioned failed report instead of a Python traceback.
Reports use schema version `1`, identify themselves as `mode: deterministic`, and
declare `providerCalls: 0`; these fields prevent consumers from confusing fixture
validation with measured provider behavior.

## Deterministic quality scoring

Measured provider results can include a `quality` object when a fixture declares
`expect`. The local scorer serializes the JSON response and checks each expected
phrase case-insensitively. This is a lightweight contract check, not semantic
LLM judging, and it never makes network calls.

Two provider reports can be compared by stable fixture ID:

```bash
python -B -m evals.compare baseline.json candidate.json \
  --min-quality-pass-rate 0.9 \
  --output evals/results/comparison.json
```

The comparison fails if a previously passing case becomes failing or if the
candidate quality pass rate falls below the selected threshold. Baseline and
candidate reports must contain the same case IDs.
Each report also records whether strict coverage was enabled and the SHA-256 digest
of the input JSONL bytes. This makes an uploaded artifact traceable to the exact
fixture content without embedding that content in the report.
Use `--strict-coverage` in CI when the fixture set must include at least one
consequential-risk contract, one `FULL` gate contract, and one `skip` action
contract. The default remains schema-only coverage validation.
The GitHub Actions workflow writes this JSON report to
`evals/results/latest.json` and uploads it as a platform-specific artifact for
14 days.

## Executable decision contracts

Fixtures may also include a `contract` object with expected deterministic routing
signals: resolved profile, task type, consequence risk, execution intent, quality
gate, and optimizer action. `npm run test:runtime` evaluates those fields through
the actual OpenCode resolver, classifier, quality gate, and decision engine. This
guards optimizer behavior without claiming to score an LLM's final answer.

Keep `expect` as the human/provider-evaluation rubric. Provider traces should
still compare OFF, AUTO, and PREVIEW on final answers, changed files, approval
events, required checks, token use, retries, and scope drift.

## Opt-in provider harness

`evals/provider.py` provides a transport-agnostic `run_provider_cases` helper for
measured runs. The caller injects the provider function; the helper never reads
credentials or performs network requests. `OFF` and `AUTO` call the provider
once per case. `PREVIEW` returns `approval_required` without calling the
provider until `approve=True` is explicitly supplied. CI continues to use the
deterministic runner and does not make provider calls.

For a local executable adapter, the provider command receives one JSON object
on stdin and must emit one JSON value on stdout. Everything after
`--provider` is the argv list; the adapter never invokes a shell:

```bash
python -m evals.provider --cases evals/cases.jsonl --mode OFF --provider python provider.py
python -m evals.provider --cases evals/cases.jsonl --mode PREVIEW --approve --provider python provider.py
python -m evals.provider --cases evals/cases.jsonl --mode MATRIX --output evals/results/matrix.json --provider python provider.py
```

The adapter has a 60-second per-case timeout by default, configurable with
`--timeout`, and a 1 MiB response limit by default, configurable with
`--max-response-bytes`. Responses are measured after compact JSON serialization
in UTF-8 bytes. Executable stdout/stderr are captured in temporary files rather
than memory; raw stdout is size-checked before UTF-8 decoding and JSON parsing,
and stderr error details are capped at 64 KiB. Provider failures are reported as command errors and credentials
remain the responsibility of the executable. A failure is isolated to its case,
later cases still run, and the report sets `passed: false`; the CLI exits with
status 1 when any case fails.
The batch defaults to at most 1000 cases; use `--max-cases` to choose a lower
or higher explicit limit. The limit is checked before any provider call.
Fixture IDs must also be unique; duplicate IDs are rejected during preflight so
that results remain safe to join across OFF, AUTO, and PREVIEW runs.
Every successful or failed report includes a `summary` object with `cases`,
`measured`, `approvalRequired`, and `failed` counts. Preflight failures use
zero counts because no cases were executed.
`MATRIX` runs OFF, AUTO, and PREVIEW and joins their results by fixture ID in a
single report. Without `--approve`, PREVIEW entries remain `approval_required`
and make no provider calls; `--approve` explicitly enables those calls.
Use repeatable `--case ID` options before `--provider` to run only selected
fixtures. Unknown IDs and malformed JSONL entries fail before provider calls;
reports record the requested IDs and selected count. The input digest continues
to identify the complete source JSONL file.
Provider payloads contain only `id`, `model`, `request`, `mode`, and optional
`expect` and `contract` values. `expect` is the provider/human rubric and must be
a non-empty string array when present; `contract` must be an object. Arbitrary
fixture metadata is not forwarded to the provider executable.
Measured and failed provider results include integer `durationMs`, measured with
a monotonic clock. Approval-gated PREVIEW entries have no duration because no
provider work occurred.
Use `--output path.json` to persist the report. Reports include the input
JSONL SHA-256 digest and never include the provider argv, preventing accidental
credential leakage through command-line arguments.
Input read, UTF-8 decode, and JSONL parse errors also produce a schema-versioned
failed report with zero provider calls and a non-zero CLI exit status. Output
files are written through a temporary sibling file before replacement.
Failed reports retain the input SHA-256 when the file was readable, and JSONL
parse messages include the one-based source line number.
