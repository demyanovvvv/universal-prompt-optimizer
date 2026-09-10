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

Developer guidance is a constraint on the optimizer, not an excuse to override the user's/project's explicit rules.

## Deterministic CI check

```bash
python -B evals/run.py
python -B evals/run.py --output evals/results/latest.json
```

The runner validates the fixture schema, model registry membership, unique IDs,
and required adversarial cases without making provider calls. It is not a
substitute for measured OFF/AUTO/PREVIEW runs; it provides a stable contract that
a future provider runner can consume without changing `cases.jsonl`.
