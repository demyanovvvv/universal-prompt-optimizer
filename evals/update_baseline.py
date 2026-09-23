#!/usr/bin/env python3
"""Regenerate the committed golden baseline from a mock matrix report.

Usage:
    python -B -m evals.update_baseline --candidate evals/results/matrix.json \
        --output evals/baselines/matrix.json

This is a maintainer action for intentional fixture or harness changes. It is
never run automatically in CI, because accepting drift silently would defeat the
regression gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from evals.baseline import summarize_matrix
except ModuleNotFoundError:  # supports direct script execution
    from baseline import summarize_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the golden matrix baseline")
    parser.add_argument("--candidate", type=Path, default=Path("evals/results/matrix.json"))
    parser.add_argument("--output", type=Path, default=Path("evals/baselines/matrix.json"))
    args = parser.parse_args()
    report = json.loads(args.candidate.read_text(encoding="utf-8"))
    baseline = summarize_matrix(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} (fingerprint {baseline['fingerprint']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
