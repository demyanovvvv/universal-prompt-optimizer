"""Exclusive scope lock used to keep installer writes from interleaving."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


class InstallLock:
    def __init__(self, path: Path, reject_symlink_components: Callable[[Path], None]) -> None:
        self.path = path
        self.acquired = False
        self._validate_path = reject_symlink_components

    def __enter__(self) -> "InstallLock":
        self._validate_path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"installation lock already exists: {self.path}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{os.getpid()}\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.acquired = True
        return self

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
