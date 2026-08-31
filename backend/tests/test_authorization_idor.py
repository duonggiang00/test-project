import json
from types import SimpleNamespace
import uuid

from sqlalchemy import func, select

from app.models.audit_event import AuditEvent
from app.models.document_chunk import DocumentChunk
from app.models.exam import Question
from app.models.material import StudyMaterial
from app.models.user import User
import app.services.ai_studio_service as ai_studio_module


def create_teacher(client, db):
    email = f"teacher_{uuid.uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Isolated Teacher",
            "role": "teacher",
            "password": "testpassword",
        },
    )
    assert response.status_code == 200
    user = db.scalar(select(User).where(User.email == email))
    user.role = "teacher"
    db.commit()
    login = client.post(
        "/auth/login",
        data={"username": email, "password": "testpassword"},
    )
    assert login.status_code == 200
    return {
        "id": user.id,
        "headers": {
            "Authorization": f"Bearer {login.json()['access_token']}"
        },
    }


def create_topic(client, actor, name):
    response = client.post(
        "/topics",
        json={"name": name, "description": "Owner-scoped topic"},
        headers=actor["headers"],
    )
    assert response.status_code == 201
    return response.json()


def create_exam(client, actor, title, *, topic_id=None, published=False):
    response = client.post(
        "/exams",
        json={
            "title": title,
            "description": "Owner-scoped exam",
            "duration_minutes": 30,
            "is_published": published,
            "topic_id": topic_id,
        },
        headers=actor["headers"],
    )
    assert response.status_code == 200
    return response.json()


def create_question(client, actor, content):
    response = client.post(
        "/questions",
        json={
            "content": content,
            "points": 1,
            "options": [
                {"content": "Correct", "is_correct": True},
                {"content": "Incorrect", "is_correct": False},
            ],
        },
        headers=actor["headers"],
    )
    assert response.status_code == 201
    return response.json()


def assert_cross_owner_matches_missing(
    client,
    *,
    path_prefix,
    cross_owner_id,
    headers,
    error_code,
):
    request_id = str(uuid.uuid4())
    request_headers = {**headers, "X-Request-ID": request_id}
    cross_owner = client.get(
        f"{path_prefix}/{cross_owner_id}",
        headers=request_headers,
    )
    missing = client.get(
        f"{path_prefix}/{uuid.uuid4()}",
        headers=request_headers,
    )

    assert cross_owner.status_code == missing.status_code == 404
    assert cross_owner.json() == missing.json()
    assert cross_owner.json() == {
        "error_code": error_code,
        "details": {},
        "request_id": request_id,
    }
    assert cross_owner.headers["X-Request-ID"] == request_id
    assert missing.headers["X-Request-ID"] == request_id
    assert str(cross_owner_id) not in cross_owner.content.decode()


def test_management_lists_are_authenticated_and_owner_scoped(
    client,
    db,
    test_teacher,
    test_student,
):
    other_teacher = create_teacher(client, db)
    owner_topic = create_topic(client, test_teacher, f"Owner {uuid.uuid4()}")
    foreign_topic = create_topic(
        client,
        other_teacher,
        f"Foreign {uuid.uuid4()}",
    )
    owner_exam = create_exam(
        client,
        test_teacher,
        f"Owner exam {uuid.uuid4()}",
        topic_id=owner_topic["id"],
        published=True,
    )
    foreign_exam = create_exam(
        client,
        other_teacher,
        f"Foreign exam {uuid.uuid4()}",
        topic_id=foreign_topic["id"],
    )

    assert client.get("/topics").status_code == 401
    assert client.get("/exams").status_code == 401
    assert (
        client.get("/exams", headers=test_student["headers"]).status_code
        == 403
    )

    owner_topics = client.get(
        "/topics",
        headers=test_teacher["headers"],
    ).json()["items"]
    owner_topic_ids = {topic["id"] for topic in owner_topics}
    assert owner_topic["id"] in owner_topic_ids
    assert foreign_topic["id"] not in owner_topic_ids

    owner_exams = client.get(
        "/exams",
        headers=test_teacher["headers"],
    ).json()["items"]
    owner_exam_ids = {exam["id"] for exam in owner_exams}
    assert owner_exam["id"] in owner_exam_ids
    assert foreign_exam["id"] not in owner_exam_ids

    student_topics = client.get(
        "/topics",
        headers=test_student["headers"],
    ).json()["items"]
    student_topic_ids = {topic["id"] for topic in student_topics}
    assert owner_topic["id"] in student_topic_ids
    assert foreign_topic["id"] not in student_topic_ids


def test_cross_owner_and_missing_details_are_indistinguishable(
    client,
    db,
    test_teacher,
):
    other_teacher = create_teacher(client, db)
    topic = create_topic(client, test_teacher, f"Private {uuid.uuid4()}")
    exam = create_exam(client, test_teacher, f"Private exam {uuid.uuid4()}")
    question = create_question(
        client,
        test_teacher,
        f"Private question {uuid.uuid4()}",
    )
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="private.txt",
        file_type="txt",
        file_path="uploads/private.txt",
        ai_status="pending",
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    for prefix, resource_id, error_code in [
        ("/topics", topic["id"], "TOPIC_NOT_FOUND"),
        ("/exams", exam["id"], "EXAM_NOT_FOUND"),
        ("/questions", question["id"], "QUESTION_NOT_FOUND"),
        ("/materials", material.id, "MATERIAL_NOT_FOUND"),
    ]:
        assert_cross_owner_matches_missing(
            client,
            path_prefix=prefix,
            cross_owner_id=resource_id,
            headers=other_teacher["headers"],
            error_code=error_code,
        )

    request_id = str(uuid.uuid4())
    download_headers = {
        **other_teacher["headers"],
        "X-Request-ID": request_id,
    }
    cross_owner_download = client.get(
        f"/materials/{material.id}/download",
        headers=download_headers,
    )
    missing_download = client.get(
        f"/materials/{uuid.uuid4()}/download",
        headers=download_headers,
    )
    assert cross_owner_download.status_code == missing_download.status_code == 404
    assert cross_owner_download.json() == missing_download.json()
    assert cross_owner_download.json()["error_code"] == "MATERIAL_NOT_FOUND"
    assert client.get(f"/materials/{material.id}/download").status_code == 401

    owner_detail = client.get(
        f"/materials/{material.id}",
        headers=test_teacher["headers"],
    )
    assert owner_detail.status_code == 200
    assert "file_path" not in owner_detail.json()


def test_bulk_assignment_is_same_owner_all_or_nothing(
    client,
    db,
    test_teacher,
):
    other_teacher = create_teacher(client, db)
    exam = create_exam(client, test_teacher, f"Bulk exam {uuid.uuid4()}")
    owned_question = create_question(
        client,
        test_teacher,
        f"Owned bulk question {uuid.uuid4()}",
    )
    foreign_question = create_question(
        client,
        other_teacher,
        f"Foreign bulk question {uuid.uuid4()}",
    )
    request_id = str(uuid.uuid4())
    headers = {**test_teacher["headers"], "X-Request-ID": request_id}

    foreign_response = client.post(
        f"/exams/{exam['id']}/questions/bulk",
        json={
            "question_ids": [owned_question["id"], foreign_question["id"]]
        },
        headers=headers,
    )
    missing_response = client.post(
        f"/exams/{exam['id']}/questions/bulk",
        json={"question_ids": [owned_question["id"], str(uuid.uuid4())]},
        headers=headers,
    )
    assert foreign_response.status_code == missing_response.status_code == 404
    assert foreign_response.json() == missing_response.json()
    assert foreign_response.json()["error_code"] == "QUESTION_NOT_FOUND"

    db.expire_all()
    assert db.get(Question, uuid.UUID(owned_question["id"])).exam_id is None
    assert db.get(Question, uuid.UUID(foreign_question["id"])).exam_id is None

    success = client.post(
        f"/exams/{exam['id']}/questions/bulk",
        json={"question_ids": [owned_question["id"]]},
        headers=test_teacher["headers"],
    )
    assert success.status_code == 200
    db.expire_all()
    persisted = db.get(Question, uuid.UUID(owned_question["id"]))
    assert str(persisted.exam_id) == exam["id"]
    assert persisted.owner_id == test_teacher["id"]

    duplicate = client.post(
        f"/exams/{exam['id']}/questions/bulk",
        json={"question_ids": [owned_question["id"], owned_question["id"]]},
        headers=test_teacher["headers"],
    )
    assert duplicate.status_code == 422


def test_legacy_null_owned_roots_are_admin_only(
    client,
    db,
    test_teacher,
    test_admin,
    test_student,
):
    from app.models.exam import Exam
    from app.models.flashcard import Flashcard, FlashcardDeck
    from app.models.topic import Topic

    topic = Topic(name=f"Legacy topic {uuid.uuid4()}", owner_id=None)
    exam = Exam(
        title=f"Legacy exam {uuid.uuid4()}",
        creator_id=None,
        duration_minutes=30,
        is_published=True,
    )
    question = Question(
        owner_id=None,
        content=f"Legacy question {uuid.uuid4()}",
        points=1,
    )
    material = StudyMaterial(
        uploader_id=None,
        title="legacy.txt",
        file_type="txt",
        file_path="uploads/legacy.txt",
        ai_status="pending",
    )
    deck = FlashcardDeck(
        topic=topic,
        title="Legacy ownerless deck",
    )
    card = Flashcard(
        deck=deck,
        front_content="Legacy front",
        back_content="Legacy back",
    )
    db.add_all([topic, exam, question, material, deck, card])
    db.commit()

    for prefix, resource in [
        ("/topics", topic),
        ("/exams", exam),
        ("/questions", question),
        ("/materials", material),
    ]:
        teacher_response = client.get(
            f"{prefix}/{resource.id}",
            headers=test_teacher["headers"],
        )
        admin_response = client.get(
            f"{prefix}/{resource.id}",
            headers=test_admin["headers"],
        )
        assert teacher_response.status_code == 404
        assert admin_response.status_code == 200

    student_topics = client.get(
        "/topics",
        headers=test_student["headers"],
    ).json()["items"]
    student_exams = client.get(
        "/student/exams",
        headers=test_student["headers"],
    ).json()["items"]
    assert str(topic.id) not in {item["id"] for item in student_topics}
    assert str(exam.id) not in {item["id"] for item in student_exams}
    assert (
        client.get(
            f"/student/exams/{exam.id}/start",
            headers=test_student["headers"],
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/flashcards/student/decks/{deck.id}/study",
            headers=test_student["headers"],
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/flashcards/student/cards/{card.id}/review",
            json={"rating": "GOOD"},
            headers=test_student["headers"],
        ).status_code
        == 404
    )


def test_student_empty_deck_topic_does_not_reveal_existence(
    client,
    test_teacher,
    test_student,
):
    private_topic = create_topic(
        client,
        test_teacher,
        f"Private empty topic {uuid.uuid4()}",
    )
    request_id = str(uuid.uuid4())
    headers = {**test_student["headers"], "X-Request-ID": request_id}

    private_response = client.get(
        f"/flashcards/topics/{private_topic['id']}/decks",
        headers=headers,
    )
    missing_response = client.get(
        f"/flashcards/topics/{uuid.uuid4()}/decks",
        headers=headers,
    )

    assert private_response.status_code == missing_response.status_code == 404
    assert private_response.json() == missing_response.json()
    assert private_response.json()["error_code"] == "TOPIC_NOT_FOUND"


def test_teacher_system_compatibility_does_not_grant_user_purge(
    client,
    test_teacher,
    test_student,
):
    list_response = client.get(
        "/admin/users",
        headers=test_teacher["headers"],
    )
    delete_response = client.delete(
        f"/admin/users/{test_student['id']}",
        headers=test_teacher["headers"],
    )
    self_promotion = client.put(
        f"/admin/users/{test_teacher['id']}/role?new_role=admin",
        headers=test_teacher["headers"],
    )

    assert list_response.status_code == 200
    assert self_promotion.status_code == 403
    assert self_promotion.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"
    assert delete_response.status_code == 403
    assert delete_response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"


def test_teacher_and_admin_cannot_use_student_self_service_routes(
    client,
    test_teacher,
    test_admin,
):
    exam_id = uuid.uuid4()
    for actor in (test_teacher, test_admin):
        responses = (
            client.get("/student/exams", headers=actor["headers"]),
            client.get(
                f"/student/exams/{exam_id}/start",
                headers=actor["headers"],
            ),
            client.post(
                f"/student/exams/{exam_id}/submit",
                json={"answers": []},
                headers=actor["headers"],
            ),
            client.get(
                f"/student/exams/{exam_id}/result",
                headers=actor["headers"],
            ),
        )
        assert all(response.status_code == 403 for response in responses)
        assert all(
            response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"
            for response in responses
        )


def test_ai_chat_context_is_limited_to_the_authorized_material(
    client,
    db,
    test_teacher,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    other_teacher = create_teacher(client, db)
    owned_material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="owned.txt",
        file_type="txt",
        file_path="uploads/owned.txt",
        ai_status="completed",
    )
    foreign_material = StudyMaterial(
        uploader_id=other_teacher["id"],
        title="foreign.txt",
        file_type="txt",
        file_path="uploads/foreign.txt",
        ai_status="completed",
    )
    db.add_all([owned_material, foreign_material])
    db.flush()
    owned_canary = f"OWNED_CONTEXT_{uuid.uuid4()}"
    sensitive_canary = f"sk-{uuid.uuid4().hex}{uuid.uuid4().hex}"
    foreign_canary = f"FOREIGN_CONTEXT_{uuid.uuid4()}"
    owned_chunk = DocumentChunk(
        material_id=owned_material.id,
        content=f"{owned_canary} {sensitive_canary}",
        embedding=[0.1] * 1536,
    )
    foreign_chunk = DocumentChunk(
        material_id=foreign_material.id,
        content=foreign_canary,
        embedding=[0.2] * 1536,
    )
    db.add_all(
        [owned_chunk, foreign_chunk]
    )
    db.commit()
    captured = {}
    provider_calls = []

    async def fake_stream(request):
        # AI-001 moved the provider SDK behind `app.ai.provider.AIProvider`;
        # patching `stream` on the shared default provider object keeps this
        # canary at the real provider boundary, which is what must never see
        # cross-owner context.
        captured["messages"] = request.messages
        provider_calls.append(request)
        return
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(
        ai_studio_module.default_provider,
        "stream",
        fake_stream,
    )
    owner_request_id = str(uuid.uuid4())
    response = client.post(
        "/ai/chat",
        json={
            "material_id": str(owned_material.id),
            "messages": [{"role": "user", "content": "Summarize lesson"}],
        },
        headers={**test_teacher["headers"], "X-Request-ID": owner_request_id},
    )

    assert response.status_code == 200
    system_context = captured["messages"][0]["content"]
    assert owned_canary in system_context
    assert foreign_canary not in system_context
    assert len(provider_calls) == 1
    db.expire_all()
    owner_chat_events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.request_id == owner_request_id,
            AuditEvent.action == "ai.chat.requested",
        )
    ).all()
    assert len(owner_chat_events) == 1
    owner_chat_event = owner_chat_events[0]
    assert owner_chat_event.actor_id == test_teacher["id"]
    assert owner_chat_event.actor_role == "teacher"
    assert owner_chat_event.owner_id == test_teacher["id"]
    assert owner_chat_event.event_metadata == {
        "prompt_version": "chat_system-v1",
        "provider": "openrouter",
        "model": "meta-llama/llama-3.1-8b-instruct",
        "retrieval_mode": "lexical",
        "context_source_ids": [str(owned_chunk.id)],
    }
    serialized_event = json.dumps(owner_chat_event.event_metadata)
    assert owned_canary not in serialized_event
    assert sensitive_canary not in serialized_event

    request_id = str(uuid.uuid4())
    idor_headers = {
        **test_teacher["headers"],
        "X-Request-ID": request_id,
    }
    cross_owner_chat = client.post(
        "/ai/chat",
        json={
            "material_id": str(foreign_material.id),
            "messages": [{"role": "user", "content": "Summarize"}],
        },
        headers=idor_headers,
    )
    missing_chat = client.post(
        "/ai/chat",
        json={
            "material_id": str(uuid.uuid4()),
            "messages": [{"role": "user", "content": "Summarize"}],
        },
        headers=idor_headers,
    )
    assert cross_owner_chat.status_code == missing_chat.status_code == 404
    assert cross_owner_chat.json() == missing_chat.json()
    assert cross_owner_chat.json()["error_code"] == "MATERIAL_NOT_FOUND"
    assert len(provider_calls) == 1

    missing_material_id = client.post(
        "/ai/chat",
        json={"messages": [{"role": "user", "content": "Summarize"}]},
        headers=test_teacher["headers"],
    )
    assert missing_material_id.status_code == 422
    assert missing_material_id.json()["error_code"] == "VALIDATION_ERROR"
    assert len(provider_calls) == 1

    assert_cross_owner_matches_missing(
        client,
        path_prefix="/materials",
        cross_owner_id=foreign_material.id,
        headers=test_teacher["headers"],
        error_code="MATERIAL_NOT_FOUND",
    )


def test_ai_chat_rejects_student_and_inactive_actor_before_provider(
    client,
    db,
    test_student,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    provider_calls = []

    async def fake_stream(request):
        provider_calls.append(request)
        return
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(ai_studio_module.default_provider, "stream", fake_stream)
    payload = {
        "material_id": str(uuid.uuid4()),
        "messages": [{"role": "user", "content": "Summarize"}],
    }

    student_response = client.post(
        "/ai/chat",
        json=payload,
        headers=test_student["headers"],
    )
    assert student_response.status_code == 403
    assert student_response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"

    inactive_teacher = create_teacher(client, db)
    inactive_user = db.get(User, inactive_teacher["id"])
    inactive_user.is_active = False
    db.commit()
    inactive_response = client.post(
        "/ai/chat",
        json=payload,
        headers=inactive_teacher["headers"],
    )
    assert inactive_response.status_code == 401
    assert inactive_response.json()["error_code"] == "UNAUTHORIZED"
    assert provider_calls == []


def test_ai_chat_admin_cross_owner_access_persists_both_audit_events(
    client,
    db,
    test_teacher,
    test_admin,
    monkeypatch,
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RAG_ENABLED", True)
    material = StudyMaterial(
        uploader_id=test_teacher["id"],
        title="admin-reviewed.txt",
        file_type="txt",
        file_path="uploads/admin-reviewed.txt",
        ai_status="completed",
    )
    db.add(material)
    db.flush()
    chunk = DocumentChunk(
        material_id=material.id,
        content="ADMIN_REVIEWED_CONTEXT",
        embedding=[0.3] * 1536,
    )
    db.add(chunk)
    db.commit()
    provider_calls = []

    async def fake_stream(request):
        provider_calls.append(request)
        return
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(ai_studio_module.default_provider, "stream", fake_stream)
    request_id = str(uuid.uuid4())
    response = client.post(
        "/ai/chat",
        json={
            "material_id": str(material.id),
            "messages": [{"role": "user", "content": "Summarize"}],
        },
        headers={**test_admin["headers"], "X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert len(provider_calls) == 1
    db.expire_all()
    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.request_id == request_id)
        .order_by(AuditEvent.action)
    ).all()
    assert [event.action for event in events] == [
        "admin.override",
        "ai.chat.requested",
    ]
    assert all(event.actor_id == test_admin["id"] for event in events)
    assert all(event.actor_role == "admin" for event in events)
    assert all(event.owner_id == test_teacher["id"] for event in events)
    assert events[0].event_metadata == {
        "permission": "read_owned_content",
        "operation": "generate",
    }
    assert events[1].event_metadata["context_source_ids"] == [str(chunk.id)]
