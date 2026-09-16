"""Explicit OpenAI-compatible provider adapter.

The caller supplies both endpoint and credential. The generic harness does not
read environment variables or credential files and this adapter is opt-in.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


def openai_compatible_provider(
    endpoint: str,
    api_key: str,
    payload: dict[str, Any],
    *,
    timeout: float = 60,
    max_response_bytes: int = 1_048_576,
    max_retries: int = 2,
    retry_backoff: float = 0.5,
) -> dict[str, Any]:
    if not endpoint or not isinstance(endpoint, str):
        raise ValueError("endpoint must be a non-empty string")
    if not api_key or not isinstance(api_key, str):
        raise ValueError("api_key must be a non-empty string")
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme != "https" and not (
        parsed_endpoint.scheme == "http" and parsed_endpoint.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("endpoint must use HTTPS, except for localhost tests")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_response_bytes < 1:
        raise ValueError("max_response_bytes must be positive")
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or not 0 <= max_retries <= 5:
        raise ValueError("max_retries must be between 0 and 5")
    if not math.isfinite(retry_backoff) or retry_backoff < 0 or retry_backoff > 30:
        raise ValueError("retry_backoff must be finite and between 0 and 30 seconds")
    request_payload = {
        "model": payload.get("model"),
        "messages": [{"role": "user", "content": payload.get("request")}],
    }
    request = Request(
        endpoint,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read(max_response_bytes + 1)
            break
        except HTTPError as exc:
            exc.close()
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == max_retries:
                raise RuntimeError(f"provider returned HTTP {exc.code}") from exc
            time.sleep(retry_backoff * (2**attempt))
        except URLError as exc:
            if attempt == max_retries:
                raise RuntimeError(f"provider request failed: {exc.reason}") from exc
            time.sleep(retry_backoff * (2**attempt))
    if len(body) > max_response_bytes:
        raise RuntimeError(f"provider response exceeds {max_response_bytes} bytes")
    try:
        decoded = json.loads(body.decode("utf-8"))
        text = decoded["choices"][0]["message"]["content"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("provider returned an invalid chat completion") from exc
    result: dict[str, Any] = {"response": {"text": text}}
    usage = decoded.get("usage")
    if isinstance(usage, dict):
        metrics: dict[str, int] = {}
        if isinstance(usage.get("prompt_tokens"), int):
            metrics["inputTokens"] = usage["prompt_tokens"]
        if isinstance(usage.get("completion_tokens"), int):
            metrics["outputTokens"] = usage["completion_tokens"]
        if metrics:
            result["metrics"] = metrics
    return result
