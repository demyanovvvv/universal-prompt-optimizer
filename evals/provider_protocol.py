"""Provider process protocol and bounded response validation."""

from __future__ import annotations

import json
import subprocess
import tempfile
from typing import Any


def call_cli_provider(command: list[str], payload: dict[str, Any], *, timeout: float, max_output_bytes: int) -> Any:
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("provider command must be a non-empty argv list")
    if max_output_bytes < 1:
        raise ValueError("max_output_bytes must be positive")
    encoded_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            completed = subprocess.run(command, input=encoded_payload, stdout=stdout_file, stderr=stderr_file,
                                       check=False, shell=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"provider timed out after {timeout:g}s") from exc
        stderr_file.seek(0)
        if completed.returncode:
            detail = stderr_file.read(65_536).decode("utf-8", errors="replace").strip() or "no stderr"
            raise RuntimeError(f"provider exited with {completed.returncode}: {detail}")
        stdout_file.seek(0, 2)
        output_bytes = stdout_file.tell()
        if output_bytes > max_output_bytes:
            raise RuntimeError(f"provider stdout exceeds {max_output_bytes} bytes")
        stdout_file.seek(0)
        try:
            output = stdout_file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"provider returned invalid UTF-8: {exc}") from exc
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"provider returned invalid JSON: {exc}") from exc
