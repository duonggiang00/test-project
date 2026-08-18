import uuid

from sqlalchemy import select

from app.db.soft_delete import soft_delete
from app.models.exam import Exam, Question
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.user import User
from app.services.content_visibility import StudentContentVisibility
from tests.test_authorization_idor import (
    create_exam,
    create_question,
    create_teacher,
    create_topic,
)


def test_include_deleted_execution_option_surfaces_soft_deleted_rows(db):
    """Direct repository-level proof of the default-exclude / opt-in mechanism.

    This does not go through any endpoint: it shows the query policy itself
    -- a plain `select(Topic)` excludes a soft-deleted row, and only a
    statement carrying `execution_options(include_deleted=True)` can see it.
    """
    topic = Topic(owner_id=None, name=f"Soft delete probe {uuid.uuid4()}")
    db.add(topic)
    db.commit()

    soft_delete(topic, None)
    db.commit()

    default_result = db.scalar(select(Topic).where(Topic.id == topic.id))
    assert default_result is None

    included_result = db.scalar(
        select(Topic)
        .where(Topic.id == topic.id)
        .execution_options(include_deleted=True)
    )
    assert included_result is not None
    assert included_result.deleted_at is not None
    assert included_result.deleted_at.tzinfo is not None


def test_delete_topic_soft_deletes_and_hides_from_normal_endpoint(client, db):
    owner = create_teacher(client, db)
    topic = create_topic(client, owner, f"Soft delete topic {uuid.uuid4()}")

    response = client.delete(f"/topics/{topic['id']}", headers=owner["headers"])
    assert response.status_code == 200

    not_found = client.get(f"/topics/{topic['id']}", headers=owner["headers"])
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "TOPIC_NOT_FOUND"

    default_row = db.scalar(select(Topic).where(Topic.id == uuid.UUID(topic["id"])))
    assert default_row is None

    deleted_row = db.scalar(
        select(Topic)
        .where(Topic.id == uuid.UUID(topic["id"]))
        .execution_options(include_deleted=True)
    )
    assert deleted_row is not None
    assert deleted_row.deleted_at is not None
    assert deleted_row.deleted_by_id == owner["id"]


def test_delete_exam_soft_deletes_and_hides_from_normal_endpoint(client, db):
    owner = create_teacher(client, db)
    exam = create_exam(client, owner, f"Soft delete exam {uuid.uuid4()}")

    response = client.delete(f"/exams/{exam['id']}", headers=owner["headers"])
    assert response.status_code == 200

    not_found = client.get(f"/exams/{exam['id']}", headers=owner["headers"])
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "EXAM_NOT_FOUND"

    deleted_row = db.scalar(
        select(Exam)
        .where(Exam.id == uuid.UUID(exam["id"]))
        .execution_options(include_deleted=True)
    )
    assert deleted_row is not None
    assert deleted_row.deleted_at is not None
    assert deleted_row.deleted_by_id == owner["id"]


def test_delete_question_soft_deletes_and_hides_from_normal_endpoint(client, db):
    owner = create_teacher(client, db)
    question = create_question(
        client, owner, f"Soft delete question {uuid.uuid4()}"
    )

    response = client.delete(
        f"/questions/{question['id']}", headers=owner["headers"]
    )
    assert response.status_code == 200

    not_found = client.get(
        f"/questions/{question['id']}", headers=owner["headers"]
    )
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "QUESTION_NOT_FOUND"

    deleted_row = db.scalar(
        select(Question)
        .where(Question.id == uuid.UUID(question["id"]))
        .execution_options(include_deleted=True)
    )
    assert deleted_row is not None
    assert deleted_row.deleted_at is not None
    assert deleted_row.deleted_by_id == owner["id"]


def test_delete_material_soft_deletes_and_hides_from_normal_endpoint(client, db):
    owner = create_teacher(client, db)
    material = StudyMaterial(
        uploader_id=owner["id"],
        title="soft-delete-probe.txt",
        file_type="txt",
        file_path="uploads/materials/soft-delete-probe-does-not-exist.txt",
        ai_status="completed",
    )
    db.add(material)
    db.commit()
    material_id = material.id

    response = client.delete(
        f"/materials/{material_id}", headers=owner["headers"]
    )
    assert response.status_code == 200

    not_found = client.get(
        f"/materials/{material_id}", headers=owner["headers"]
    )
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "MATERIAL_NOT_FOUND"

    deleted_row = db.scalar(
        select(StudyMaterial)
        .where(StudyMaterial.id == material_id)
        .execution_options(include_deleted=True)
    )
    assert deleted_row is not None
    assert deleted_row.deleted_at is not None
    assert deleted_row.deleted_by_id == owner["id"]


def test_cascade_material_delete_soft_deletes_linked_questions(client, db):
    owner = create_teacher(client, db)
    material = StudyMaterial(
        uploader_id=owner["id"],
        title="cascade-probe.txt",
        file_type="txt",
        file_path="uploads/materials/cascade-probe-does-not-exist.txt",
        ai_status="completed",
    )
    db.add(material)
    db.flush()
    linked_question = Question(
        owner_id=owner["id"],
        material_id=material.id,
        content="Cascade-linked question",
    )
    db.add(linked_question)
    db.commit()
    material_id = material.id
    question_id = linked_question.id

    response = client.delete(
        f"/materials/{material_id}?cascade=true", headers=owner["headers"]
    )
    assert response.status_code == 200

    # Default reads exclude both the material and the cascaded question --
    # they were soft-deleted, not hard-deleted.
    assert db.scalar(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    ) is None
    assert db.scalar(select(Question).where(Question.id == question_id)) is None

    deleted_question = db.scalar(
        select(Question)
        .where(Question.id == question_id)
        .execution_options(include_deleted=True)
    )
    assert deleted_question is not None
    assert deleted_question.deleted_at is not None
    assert deleted_question.deleted_by_id == owner["id"]


def test_delete_user_soft_deletes_and_hides_from_admin_endpoints(
    client, db, test_admin
):
    email = f"soft_delete_student_{uuid.uuid4()}@example.com"
    register = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Soft Delete Student",
            "role": "student",
            "password": "testpassword",
        },
    )
    assert register.status_code == 200
    user_id = register.json()["id"]

    response = client.delete(
        f"/admin/users/{user_id}", headers=test_admin["headers"]
    )
    assert response.status_code == 200

    not_found = client.get(
        f"/admin/users/{user_id}", headers=test_admin["headers"]
    )
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "USER_NOT_FOUND"

    default_row = db.scalar(select(User).where(User.id == uuid.UUID(user_id)))
    assert default_row is None

    deleted_row = db.scalar(
        select(User)
        .where(User.id == uuid.UUID(user_id))
        .execution_options(include_deleted=True)
    )
    assert deleted_row is not None
    assert deleted_row.deleted_at is not None
    assert deleted_row.deleted_by_id == test_admin["id"]


def test_student_visibility_raw_selects_exclude_soft_deleted_topic_and_exam(
    client, db
):
    """Verify the raw select() statements in StudentContentVisibility are
    covered by the global soft-delete filter (not just db.scalar(select(Model))
    call sites elsewhere in the service layer)."""
    owner = create_teacher(client, db)
    topic = create_topic(client, owner, f"Visible topic {uuid.uuid4()}")
    exam = create_exam(
        client,
        owner,
        f"Visible exam {uuid.uuid4()}",
        topic_id=topic["id"],
        published=True,
    )
    topic_id = uuid.UUID(topic["id"])
    exam_id = uuid.UUID(exam["id"])

    visible_topic = db.scalar(
        StudentContentVisibility.topic_statement().where(Topic.id == topic_id)
    )
    assert visible_topic is not None
    visible_exam = db.scalar(
        StudentContentVisibility.exam_statement().where(Exam.id == exam_id)
    )
    assert visible_exam is not None

    exam_row = db.scalar(select(Exam).where(Exam.id == exam_id))
    soft_delete(exam_row, owner["id"])
    topic_row = db.scalar(select(Topic).where(Topic.id == topic_id))
    soft_delete(topic_row, owner["id"])
    db.commit()

    assert (
        db.scalar(
            StudentContentVisibility.topic_statement().where(Topic.id == topic_id)
        )
        is None
    )
    assert (
        db.scalar(
            StudentContentVisibility.exam_statement().where(Exam.id == exam_id)
        )
        is None
    )
