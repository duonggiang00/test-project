from uuid import uuid4
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from app.services.material_service import MaterialService


class RecordingStorage:
    def __init__(self) -> None:
        self.deleted_paths: list[str] = []

    def save(self, filename: str, content: bytes) -> str:
        return f"uploads/materials/persisted-{filename}"

    def delete(self, stored_path: str) -> None:
        self.deleted_paths.append(stored_path)


class FailingCommitSession:
    def __init__(self) -> None:
        self.rollback_called = False

    def add(self, instance: object) -> None:
        pass

    def commit(self) -> None:
        raise RuntimeError("simulated database failure")

    def refresh(self, instance: object) -> None:
        pass

    def rollback(self) -> None:
        self.rollback_called = True


def test_failed_material_commit_rolls_back_and_removes_stored_file():
    database = FailingCommitSession()
    storage = RecordingStorage()

    with pytest.raises(RuntimeError, match="simulated database failure"):
        MaterialService.upload_material(
            db=database,
            current_user=SimpleNamespace(id=uuid4(), role="teacher"),
            filename="lesson.txt",
            content_type="text/plain",
            content=b"content",
            background_tasks=BackgroundTasks(),
            storage=storage,
        )

    assert database.rollback_called is True
    assert storage.deleted_paths == ["uploads/materials/persisted-lesson.txt"]
