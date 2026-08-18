from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, unquote
from uuid import uuid4


class FileStorage(Protocol):
    """Replaceable boundary for persisted upload content."""

    def save(self, filename: str, content: bytes) -> str: ...

    def delete(self, stored_path: str) -> None: ...

    def resolve_for_read(self, stored_path: str) -> Path: ...

    def quarantine(self, stored_path: str) -> str: ...

    def restore_from_quarantine(self, quarantine_token: str) -> str: ...

    def finalize_purge(self, quarantine_token: str) -> None: ...


class LocalFileStorage:
    """Store files below a configured local root without trusting user paths."""

    QUARANTINE_NAMESPACE = "_quarantine"

    def __init__(self, root: Path | str, namespace: str = "materials") -> None:
        self.root = Path(root)
        self.namespace = namespace
        self._resolved_root = self.root.resolve()
        self._target_directory = (self.root / namespace).resolve()
        self._assert_within_root(self._target_directory)
        self._quarantine_directory = (
            self.root / self.QUARANTINE_NAMESPACE
        ).resolve()
        self._assert_within_root(self._quarantine_directory)

    def ensure_root(self) -> None:
        self._target_directory.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name
        if not safe_name or safe_name != filename:
            raise ValueError("unsafe storage filename")

        suffix = Path(safe_name).suffix.lower()
        self.ensure_root()
        stored_path = self.root / self.namespace / f"{uuid4().hex}{suffix}"
        destination = stored_path.resolve()
        self._assert_within_root(destination)

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self._target_directory, delete=False
            ) as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

        return str(stored_path)

    def delete(self, stored_path: str) -> None:
        candidate = Path(stored_path).resolve()
        self._assert_within_root(candidate)
        candidate.unlink(missing_ok=True)

    def resolve_for_read(self, stored_path: str) -> Path:
        candidate = Path(stored_path).resolve()
        self._assert_within_root(candidate)
        if not candidate.is_file():
            raise FileNotFoundError(stored_path)
        return candidate

    def quarantine(self, stored_path: str) -> str:
        """Atomically move a file out of active storage into quarantine.

        Reversible: the returned token round-trips through
        `restore_from_quarantine` back to the exact original path. Used by
        purge so a file can be pulled out of active service before its
        metadata row is hard-deleted, without losing the ability to put it
        back if the accompanying database transaction fails.
        """
        source = Path(stored_path).resolve()
        self._assert_within_root(source)
        if not source.is_file():
            raise FileNotFoundError(stored_path)

        original_relative = source.relative_to(self._resolved_root).as_posix()
        self._quarantine_directory.mkdir(parents=True, exist_ok=True)
        token_name = f"{uuid4().hex}__{quote(original_relative, safe='')}"
        destination = (self._quarantine_directory / token_name).resolve()
        self._assert_within_root(destination)
        os.replace(source, destination)
        return str(destination)

    def restore_from_quarantine(self, quarantine_token: str) -> str:
        """Move a quarantined file back to its original active-storage path."""
        quarantined = Path(quarantine_token).resolve()
        self._assert_within_root(quarantined)
        if quarantined.parent != self._quarantine_directory:
            raise ValueError("quarantine token outside quarantine namespace")
        _, separator, encoded_original = quarantined.name.partition("__")
        if not separator or not encoded_original:
            raise ValueError("malformed quarantine token")

        original_relative = unquote(encoded_original)
        destination = (self.root / original_relative).resolve()
        self._assert_within_root(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(quarantined, destination)
        return str(self.root / original_relative)

    def finalize_purge(self, quarantine_token: str) -> None:
        """Permanently delete a quarantined file.

        Only safe to call after the database transaction that removed the
        owning metadata row has committed successfully.
        """
        quarantined = Path(quarantine_token).resolve()
        self._assert_within_root(quarantined)
        if quarantined.parent != self._quarantine_directory:
            raise ValueError("quarantine token outside quarantine namespace")
        quarantined.unlink(missing_ok=True)

    def _assert_within_root(self, candidate: Path) -> None:
        if not candidate.is_relative_to(self._resolved_root):
            raise ValueError("storage path escapes configured root")


material_file_storage = LocalFileStorage(Path("uploads"))
