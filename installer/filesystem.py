"""Small filesystem primitives used by the installer plan executor."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _validate_destination(path: Path) -> None:
    if path.exists() and not path.is_file():
        raise ValueError(f"expected a file destination: {path}")
    if path.is_symlink():
        raise ValueError(f"refusing to write through symlink: {path}")


def atomic_write_bytes(path: Path, value: bytes) -> None:
    _validate_destination(path)
    mode = path.stat().st_mode if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if mode is not None:
            path.chmod(mode)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def atomic_write_text(path: Path, value: str) -> None:
    atomic_write_bytes(path, value.encode("utf-8"))
