"""Explicit rollback transaction for installer operations."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path

from .filesystem import atomic_write_bytes

TransactionProvider = ContextVar["InstallTransaction | None"]("prompt_optimizer_install_transaction", default=None)


@dataclass
class InstallTransaction:
    snapshots: dict[Path, tuple[bytes, int] | None] = field(default_factory=dict)
    created_directories: list[Path] = field(default_factory=list)
    defer_directory_cleanup: bool = False
    _token: Token["InstallTransaction | None"] | None = field(default=None, init=False, repr=False)
    _directory_cleanup_pending: bool = field(default=False, init=False, repr=False)

    def __enter__(self) -> "InstallTransaction":
        self._token = TransactionProvider.set(self)
        return self

    def __exit__(self, exc_type, _exc, _traceback) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            if self._token is not None:
                TransactionProvider.reset(self._token)
                self._token = None


    def mkdir(self, path: Path) -> None:
        missing = []
        current = path
        while not current.exists():
            missing.append(current)
            current = current.parent
        path.mkdir(parents=True, exist_ok=True)
        self.created_directories.extend(reversed(missing))

    def record(self, path: Path) -> None:
        path = path.resolve()
        if path in self.snapshots:
            return
        if path.exists():
            if not path.is_file():
                raise ValueError(f"expected a file destination: {path}")
            self.snapshots[path] = (path.read_bytes(), path.stat().st_mode)
        else:
            self.snapshots[path] = None

    def rollback(self) -> None:
        token = self._token
        if token is not None:
            TransactionProvider.reset(token)
            self._token = None
        for path, snapshot in reversed(list(self.snapshots.items())):
            if snapshot is None:
                if path.exists() and path.is_file():
                    path.unlink()
                continue
            content, mode = snapshot
            atomic_write_bytes(path, content)
        self._directory_cleanup_pending = True
        if not self.defer_directory_cleanup:
            self.prune_created_directories()
        if token is not None:
            self._token = TransactionProvider.set(self)

    def prune_created_directories(self) -> None:
        if not self._directory_cleanup_pending:
            return
        for path in reversed(self.created_directories):
            try:
                path.rmdir()
            except OSError:
                pass
        self.created_directories.clear()
        self._directory_cleanup_pending = False


def record_path(path: Path) -> None:
    transaction = TransactionProvider.get()
    if transaction is not None:
        transaction.record(path)
