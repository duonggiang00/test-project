from pathlib import Path

import pytest

from app.core.file_storage import LocalFileStorage


def test_quarantine_round_trip_restores_exact_original_path(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    stored_path = storage.save("lesson.txt", b"hello quarantine")

    token = storage.quarantine(stored_path)
    assert not Path(stored_path).exists()
    assert Path(token).is_file()

    restored_path = storage.restore_from_quarantine(token)
    assert restored_path == stored_path
    assert Path(stored_path).is_file()
    assert Path(stored_path).read_bytes() == b"hello quarantine"


def test_finalize_purge_permanently_deletes_quarantined_file(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    stored_path = storage.save("lesson.txt", b"finalize me")
    token = storage.quarantine(stored_path)

    storage.finalize_purge(token)

    assert not Path(token).exists()
    assert not Path(stored_path).exists()


def test_quarantine_rejects_path_outside_root(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    outside = tmp_path.parent / f"outside-{tmp_path.name}.txt"
    outside.write_bytes(b"nope")
    try:
        with pytest.raises(ValueError):
            storage.quarantine(str(outside))
    finally:
        outside.unlink(missing_ok=True)


def test_restore_from_quarantine_rejects_forged_token(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    forged = tmp_path / "materials" / "not-a-quarantine-token.txt"
    forged.parent.mkdir(parents=True, exist_ok=True)
    forged.write_bytes(b"forged")

    with pytest.raises(ValueError):
        storage.restore_from_quarantine(str(forged))


def test_quarantine_missing_file_raises_file_not_found(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    with pytest.raises(FileNotFoundError):
        storage.quarantine(str(tmp_path / "materials" / "missing.txt"))


def test_finalize_purge_rejects_token_outside_quarantine_namespace(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    stored_path = storage.save("lesson.txt", b"not quarantined")

    with pytest.raises(ValueError):
        storage.finalize_purge(stored_path)

    # Untouched -- the rejected call must not delete the active file.
    assert Path(stored_path).is_file()
