from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class FileStorage(Protocol):
    """Replaceable boundary for persisted upload content."""

    def save(self, filename: str, content: bytes) -> str: ...

    def delete(self, stored_path: str) -> None: ...


class LocalFileStorage:
    """Store files below a configured local root without trusting user paths."""

    def __init__(self, root: Path | str, namespace: str = "materials") -> None:
        self.root = Path(root)
        self.namespace = namespace
        self._resolved_root = self.root.resolve()
        self._target_directory = (self.root / namespace).resolve()
        self._assert_within_root(self._target_directory)

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

    def _assert_within_root(self, candidate: Path) -> None:
        if not candidate.is_relative_to(self._resolved_root):
            raise ValueError("storage path escapes configured root")


material_file_storage = LocalFileStorage(Path("uploads"))
