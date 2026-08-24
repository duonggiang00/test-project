from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings, settings
from app.main import app


def test_rag_is_disabled_by_default():
    assert Settings.model_fields["RAG_ENABLED"].default is False


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/ai/chat",
            {
                "material_id": "4cf8741b-f27f-4bfd-ac33-639f1d2734b4",
                "messages": [{"role": "user", "content": "Summarize"}],
            },
        ),
        (
            "/ai/process-document",
            {"material_id": "4cf8741b-f27f-4bfd-ac33-639f1d2734b4"},
        ),
    ],
)
def test_disabled_rag_routes_fail_before_authentication(monkeypatch, path, payload):
    monkeypatch.setattr(settings, "RAG_ENABLED", False)

    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "FEATURE_NOT_AVAILABLE"
    assert body["details"] == {}
    assert isinstance(body["request_id"], str)
    assert body["request_id"]
