"""DATA-009: the 30-day file lifecycle applied to material downloads.

Soft-delete (DATA-003), restore (DATA-004), and purge (DATA-005) already
exist as independent building blocks. This file proves
`GET /materials/{material_id}/download` actually honors that lifecycle
end-to-end, rather than assuming it does because the pieces exist.

It also regression-guards the one real production gap this phase found:
`delete_material` used to call `storage.delete(file_path)` unconditionally
the moment a material was soft-deleted -- long before the 30-day purge
boundary `purge_service` uses. That silently broke restore: the metadata row
came back with `deleted_at` cleared, but the underlying file was already
gone, so the download stayed 404 forever instead of recovering. Soft delete
must leave the file exactly where it is; only `purge_service.apply_purge`
(after the 30-day window) is allowed to remove it for good.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.exceptions import AppException
from app.core.file_storage import LocalFileStorage
from app.db.soft_delete import RESTORE_WINDOW
from app.models.material import StudyMaterial
from app.services.material_service import MaterialService
from app.services.purge_service import apply_purge
from tests.test_authorization_idor import create_teacher


def _admin_actor(test_admin):
    return SimpleNamespace(id=test_admin["id"], role="admin")


def _make_storage(tmp_path):
    storage = LocalFileStorage(tmp_path, namespace="materials")
    storage.ensure_root()
    return storage


def _body_without_request_id(response):
    """Response JSON with the per-request correlation ID stripped.

    Two independent requests always carry different `X-Request-ID`s unless
    the caller explicitly pins one, so comparing raw `.json()` output across
    separate calls would spuriously fail on that field alone. Everything
    else -- `error_code` and `details` -- must still match exactly for two
    responses to be considered canonically equivalent.
    """
    body = response.json()
    return {key: value for key, value in body.items() if key != "request_id"}


def _create_material(db, storage, owner_id, *, content=b"lifecycle content"):
    file_path = storage.save(f"{uuid.uuid4()}.txt", content)
    material = StudyMaterial(
        uploader_id=owner_id,
        title="lifecycle.txt",
        file_type="txt",
        file_path=file_path,
        ai_status="completed",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def test_soft_delete_keeps_the_file_recoverable_for_restore(client, db, tmp_path):
    """Core regression guard: soft delete must not touch storage at all.

    Proves the file itself (not just the DB row) survives a delete/restore
    cycle, and that the owner is denied a download while soft-deleted even
    though the bytes are still sitting untouched on disk -- the default
    session filter (DATA-003), not file absence, is what enforces the
    denial.
    """
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    material = _create_material(db, storage, owner["id"])
    original_path = material.file_path
    actor = SimpleNamespace(id=owner["id"], role="teacher")

    MaterialService.delete_material(db, material.id, actor, storage=storage)

    # Day zero of a 30-day window: nothing purge-worthy has happened, so the
    # file must still be physically present and byte-identical.
    resolved = storage.resolve_for_read(original_path)
    assert resolved.is_file()
    assert resolved.read_bytes() == b"lifecycle content"

    # The owner cannot download their own material while it is soft-deleted,
    # even though they could restore it first -- the download path must not
    # accidentally read with `include_deleted=True`.
    with pytest.raises(AppException) as denied:
        MaterialService.get_material_download(db, material.id, actor, storage=storage)
    assert denied.value.status_code == 404
    assert denied.value.error_code == "MATERIAL_NOT_FOUND"

    # Restore brings the row back, and the download succeeds again with the
    # exact original bytes -- the file lifecycle survives the full
    # delete -> restore cycle, not just the metadata.
    MaterialService.restore_material(db, material.id, actor)
    path, _filename = MaterialService.get_material_download(
        db, material.id, actor, storage=storage
    )
    assert path == resolved
    assert path.read_bytes() == b"lifecycle content"


def test_http_download_full_cycle_preserves_bytes_and_headers(client, test_teacher):
    """End-to-end HTTP proof of the same cycle, including response headers.

    Mirrors the assertion the frontend BFF proxy contract test makes about a
    downstream backend response (exact bytes, `Content-Type`, and
    `Content-Disposition` all preserved) -- here proven against the real
    backend endpoint rather than a mocked one.
    """
    files = {"file": ("lesson.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")}
    upload = client.post(
        "/materials/upload", files=files, headers=test_teacher["headers"]
    )
    assert upload.status_code == 200
    material_id = upload.json()["id"]

    def _download():
        return client.get(
            f"/materials/{material_id}/download", headers=test_teacher["headers"]
        )

    first = _download()
    assert first.status_code == 200
    assert first.content == b"%PDF-1.4 fake pdf bytes"
    assert first.headers["content-type"] == "application/pdf"
    assert 'filename="lesson.pdf"' in first.headers["content-disposition"]

    delete_res = client.delete(
        f"/materials/{material_id}", headers=test_teacher["headers"]
    )
    assert delete_res.status_code == 200

    denied = _download()
    assert denied.status_code == 404
    assert denied.json()["error_code"] == "MATERIAL_NOT_FOUND"

    restore_res = client.post(
        f"/materials/{material_id}/restore", headers=test_teacher["headers"]
    )
    assert restore_res.status_code == 200

    second = _download()
    assert second.status_code == 200
    assert second.content == first.content
    assert second.headers["content-type"] == first.headers["content-type"]
    assert (
        second.headers["content-disposition"] == first.headers["content-disposition"]
    )


def test_purged_material_download_is_canonical_not_found(
    client, db, test_admin, tmp_path
):
    """After a real purge, download must fail the same way as any 404.

    Runs the actual allowlisted `purge_service.apply_purge` (DATA-005), not
    a stand-in, then proves both the row and the file are truly gone and
    that the download endpoint gives no distinguishable error for "purged"
    versus "never existed".
    """
    owner = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)
    material = _create_material(db, storage, owner["id"])
    material_id = str(material.id)
    original_path = material.file_path

    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1)
    material.deleted_at = expired
    material.deleted_by_id = owner["id"]
    db.commit()

    report = apply_purge(db, admin_actor, storage=storage)
    assert material.id in report.purged_ids

    with pytest.raises(FileNotFoundError):
        storage.resolve_for_read(original_path)

    owner_response = client.get(
        f"/materials/{material_id}/download", headers=owner["headers"]
    )
    missing_response = client.get(
        f"/materials/{uuid.uuid4()}/download", headers=owner["headers"]
    )
    assert owner_response.status_code == missing_response.status_code == 404
    assert _body_without_request_id(owner_response) == _body_without_request_id(
        missing_response
    )
    assert owner_response.json()["error_code"] == "MATERIAL_NOT_FOUND"


def test_full_lifecycle_not_found_is_canonical_at_every_stage(
    client, db, test_admin, tmp_path
):
    """Cross-owner and missing-ID requests stay indistinguishable throughout.

    Batch B already proved this for an active record. This walks the same
    material through active -> soft-deleted -> purged and re-checks the
    equivalence at each stage, including the owner's own view once the
    material is soft-deleted or purged -- soft deletion or purge must never
    create a third, distinguishable "it exists but..." error path that would
    leak existence to a non-owner.
    """
    owner = create_teacher(client, db)
    other_teacher = create_teacher(client, db)
    storage = _make_storage(tmp_path)
    admin_actor = _admin_actor(test_admin)
    material = _create_material(db, storage, owner["id"])
    material_id = str(material.id)
    missing_id = str(uuid.uuid4())

    def _download(headers, target_id=material_id):
        return client.get(f"/materials/{target_id}/download", headers=headers)

    # Stage 1: active record. Cross-owner == missing.
    cross = _download(other_teacher["headers"])
    missing = _download(other_teacher["headers"], missing_id)
    assert cross.status_code == missing.status_code == 404
    assert _body_without_request_id(cross) == _body_without_request_id(missing)
    assert cross.json()["error_code"] == "MATERIAL_NOT_FOUND"

    # Stage 2: soft-deleted. Owner == cross-owner == missing.
    delete_res = client.delete(
        f"/materials/{material_id}", headers=owner["headers"]
    )
    assert delete_res.status_code == 200

    owner_deleted = _download(owner["headers"])
    cross_deleted = _download(other_teacher["headers"])
    missing_deleted = _download(owner["headers"], missing_id)
    assert (
        owner_deleted.status_code
        == cross_deleted.status_code
        == missing_deleted.status_code
        == 404
    )
    assert (
        _body_without_request_id(owner_deleted)
        == _body_without_request_id(cross_deleted)
        == _body_without_request_id(missing_deleted)
    )
    assert owner_deleted.json()["error_code"] == "MATERIAL_NOT_FOUND"

    # Stage 3: purged. Owner == cross-owner == missing, still.
    db.expire_all()
    material = db.scalar(
        select(StudyMaterial)
        .where(StudyMaterial.id == material.id)
        .execution_options(include_deleted=True)
    )
    expired = datetime.now(timezone.utc) - RESTORE_WINDOW - timedelta(days=1)
    material.deleted_at = expired
    db.commit()
    report = apply_purge(db, admin_actor, storage=storage)
    assert material.id in report.purged_ids

    owner_purged = _download(owner["headers"])
    cross_purged = _download(other_teacher["headers"])
    missing_purged = _download(owner["headers"], missing_id)
    assert (
        owner_purged.status_code
        == cross_purged.status_code
        == missing_purged.status_code
        == 404
    )
    assert (
        _body_without_request_id(owner_purged)
        == _body_without_request_id(cross_purged)
        == _body_without_request_id(missing_purged)
    )
    assert owner_purged.json()["error_code"] == "MATERIAL_NOT_FOUND"
