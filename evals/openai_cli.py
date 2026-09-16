#!/usr/bin/env python3
"""Explicit stdin/stdout adapter for a trusted OpenAI-compatible eval run."""

from __future__ import annotations

import json
import os
import sys

try:
    from evals.http_provider import openai_compatible_provider
except ModuleNotFoundError:  # supports direct execution by subprocess adapters
    from http_provider import openai_compatible_provider


def main() -> int:
    endpoint = os.environ.get("OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2
    try:
        payload = json.load(sys.stdin.buffer)
        result = openai_compatible_provider(endpoint, api_key, payload)
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
