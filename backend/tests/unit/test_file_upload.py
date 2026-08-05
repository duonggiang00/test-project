import io
import zipfile
from pathlib import Path

import pytest

from app.core.file_storage import LocalFileStorage
from app.core.security_guardrails import MAX_FILE_SIZE_BYTES, validate_file_upload


def _office_document(required_entry: str) -> bytes:
    content = io.BytesIO()
    with zipfile.ZipFile(content, mode="w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(required_entry, "<document />")
    return content.getvalue()


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("lesson.pdf", "application/pdf", b"%PDF-1.7\ncontent"),
        (
            "lesson.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _office_document("word/document.xml"),
        ),
        (
            "lesson.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            _office_document("ppt/presentation.xml"),
        ),
        ("lesson.txt", "text/plain; charset=utf-8", b"Plain UTF-8 text"),
    ],
)
def test_approved_upload_types_require_matching_mime_and_signature(
    filename: str, content_type: str, content: bytes
):
    assert validate_file_upload(filename, content_type, content) == (True, "")


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "error_code"),
    [
        ("../lesson.txt", "text/plain", b"text", "INVALID_FILENAME"),
        ("lesson.exe", "application/octet-stream", b"binary", "UNSUPPORTED_FILE_TYPE"),
        ("lesson.pdf", "text/plain", b"%PDF-1.7", "INVALID_FILE_CONTENT_TYPE"),
        ("lesson.pdf", "application/pdf", b"not a PDF", "INVALID_FILE_CONTENT"),
        (
            "lesson.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _office_document("ppt/presentation.xml"),
            "INVALID_FILE_CONTENT",
        ),
        (
            "lesson.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            b"not a zip archive",
            "INVALID_FILE_CONTENT",
        ),
        ("lesson.txt", "text/plain", b"\xff", "INVALID_FILE_CONTENT"),
        ("lesson.txt", "text/plain", b"invalid\x00text", "INVALID_FILE_CONTENT"),
    ],
)
def test_upload_validation_rejects_path_type_mime_and_signature_mismatches(
    filename: str, content_type: str, content: bytes, error_code: str
):
    assert validate_file_upload(filename, content_type, content) == (False, error_code)


def test_upload_validation_rejects_content_over_50_mb():
    oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)

    assert validate_file_upload("lesson.txt", "text/plain", oversized) == (
        False,
        "FILE_TOO_LARGE",
    )


def test_local_storage_uses_unique_names_and_preserves_extension(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)

    first = Path(storage.save("lesson.txt", b"first"))
    second = Path(storage.save("lesson.txt", b"second"))

    assert first != second
    assert first.parent == tmp_path / "materials"
    assert first.suffix == ".txt"
    assert first.read_bytes() == b"first"
    assert second.read_bytes() == b"second"

    storage.delete(str(first))
    assert not first.exists()
    assert second.exists()


def test_local_storage_refuses_paths_outside_its_root(tmp_path: Path):
    storage = LocalFileStorage(tmp_path / "uploads")

    with pytest.raises(ValueError, match="unsafe storage filename"):
        storage.save("../outside.txt", b"content")

    with pytest.raises(ValueError, match="escapes configured root"):
        storage.delete(str(tmp_path / "outside.txt"))


def test_local_storage_removes_temporary_file_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    storage = LocalFileStorage(tmp_path)

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("app.core.file_storage.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        storage.save("lesson.txt", b"content")

    assert list((tmp_path / "materials").iterdir()) == []
