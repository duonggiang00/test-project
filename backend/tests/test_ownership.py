import uuid

import pytest
from sqlalchemy import select

from app.models.material import StudyMaterial
from app.models.user import User


def create_teacher(client, db):
    email = f"teacher_{uuid.uuid4()}@example.com"
    register_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Non-owner Teacher",
            "role": "teacher",
            "password": "testpassword",
        },
    )
    assert register_response.status_code == 200

    user = db.scalar(select(User).where(User.email == email))
    user.role = "teacher"
    db.commit()

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": "testpassword"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {
        "id": user.id,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def exam_update_payload(title):
    return {
        "title": title,
        "description": "Ownership matrix",
        "duration_minutes": 30,
        "is_published": False,
    }


def test_exam_update_authorization_matrix(
    client,
    db,
    sample_exam,
    test_student,
    test_admin,
):
    exam_id = sample_exam["exam"]["id"]
    non_owner = create_teacher(client, db)

    anonymous_response = client.put(
        f"/exams/{exam_id}",
        json=exam_update_payload("Anonymous update"),
    )
    assert anonymous_response.status_code == 401

    student_response = client.put(
        f"/exams/{exam_id}",
        json=exam_update_payload("Student update"),
        headers=test_student["headers"],
    )
    assert student_response.status_code == 403
    assert student_response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"

    owner_response = client.put(
        f"/exams/{exam_id}",
        json=exam_update_payload("Owner update"),
        headers=sample_exam["teacher"]["headers"],
    )
    assert owner_response.status_code == 200

    non_owner_response = client.put(
        f"/exams/{exam_id}",
        json=exam_update_payload("Non-owner update"),
        headers=non_owner["headers"],
    )
    assert non_owner_response.status_code == 403
    assert non_owner_response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"

    admin_response = client.put(
        f"/exams/{exam_id}",
        json=exam_update_payload("Admin update"),
        headers=test_admin["headers"],
    )
    assert admin_response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    reason="SEC-002: bulk question assignment does not enforce exam ownership",
)
def test_non_owner_teacher_cannot_bulk_assign_questions(client, db, sample_exam):
    non_owner = create_teacher(client, db)
    response = client.post(
        f"/exams/{sample_exam['exam']['id']}/questions/bulk",
        json={"question_ids": [question["id"] for question in sample_exam["questions"]]},
        headers=non_owner["headers"],
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"


@pytest.mark.xfail(
    strict=True,
    reason="SEC-002: material detail does not scope access by uploader/admin",
)
def test_non_owner_teacher_cannot_read_material(client, db, test_teacher):
    owner = db.scalar(select(User).where(User.email == test_teacher["email"]))
    material = StudyMaterial(
        uploader_id=owner.id,
        title="private.txt",
        file_type="txt",
        file_path="uploads/private.txt",
        ai_status="pending",
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    non_owner = create_teacher(client, db)
    response = client.get(
        f"/materials/{material.id}",
        headers=non_owner["headers"],
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "NOT_ENOUGH_PERMISSIONS"
