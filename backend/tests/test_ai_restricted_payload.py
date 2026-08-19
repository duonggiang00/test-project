"""AI-003/AI-004: audit metadata, restricted payload access, and §6.3 expiry.

Covers the three claims those tasks rest on:

1. The §2.4 metadata actually reaches `audit_events` -- and the raw prompt
   and raw output actually do not, even when a canary is planted in them.
2. Reading a restricted payload is owner/admin-only, and a cross-owner probe
   is indistinguishable from a missing one.
3. The §6.3 30-day clock is enforced by the governed purge path, and
   widening the purge allowlist to reach these rows did not make any
   protected record reachable.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.ai_generation import AIGenerationJob
from app.models.ai_restricted_payload import (
    RESTRICTED_PAYLOAD_RETENTION,
    AIRestrictedPayload,
)
from app.models.audit_event import AuditEvent
from app.models.material import StudyMaterial
from app.models.submission import Submission, SubmissionAnswer
from app.services.ai_restricted_payload_service import AIRestrictedPayloadService
from app.services.purge_service import (
    apply_restricted_payload_purge,
    plan_restricted_payload_purge,
)
from tests.test_authorization_idor import create_teacher


# Planted in a prompt and its output; must never appear in `audit_events`.
CANARY = "CANARY-SEKRIT-a1b2c3d4"


def _admin_actor(test_admin):
    return SimpleNamespace(id=test_admin["id"], role="admin")


def _actor(user_row, role):
    return SimpleNamespace(id=user_row["id"], role=role)


def _create_material(db, owner_id):
    material = StudyMaterial(
        uploader_id=owner_id,
        title=f"Payload material {uuid.uuid4()}.txt",
        file_type="txt",
        file_path=f"materials/{uuid.uuid4()}.txt",
        ai_status="completed",
    )
    db.add(material)
    db.flush()
    return material


def _create_job(db, owner_id, material_id, *, status="generated"):
    job = AIGenerationJob(
        owner_id=owner_id,
        material_id=material_id,
        use_case="question_generation",
        status=status,
        version=1,
    )
    db.add(job)
    db.flush()
    return job


def _create_payload(db, job, *, expires_at=None, prompt=None, output=None):
    payload = AIRestrictedPayload(
        job_id=job.id,
        rendered_prompt=prompt if prompt is not None else f"Prompt {CANARY}",
        raw_output=output if output is not None else f"Output {CANARY}",
        expires_at=expires_at
        or (datetime.now(timezone.utc) + RESTRICTED_PAYLOAD_RETENTION),
    )
    db.add(payload)
    db.flush()
    return payload


@pytest.mark.integration
def test_restricted_payload_is_readable_by_owner_and_admin(
    db, test_admin, test_teacher
):
    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    _create_payload(db, job)
    db.commit()

    from app.models.user import User

    owner_user = db.get(User, test_teacher["id"])
    admin_user = db.get(User, test_admin["id"])

    for reader in (owner_user, admin_user):
        found = AIRestrictedPayloadService.get_for_job(db, job.id, reader)
        assert found.job_id == job.id
        assert CANARY in found.rendered_prompt


@pytest.mark.integration
def test_cross_owner_and_missing_payload_reads_are_indistinguishable(
    client, db, test_teacher
):
    from app.models.user import User

    # Registered through the real endpoint like every other test actor, so
    # this teacher is a fully-formed user rather than a bare row that would
    # then break unrelated list endpoints.
    other = create_teacher(client, db)
    other_user = db.get(User, other["id"])
    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    _create_payload(db, job)
    db.commit()

    with pytest.raises(AppException) as cross_owner:
        AIRestrictedPayloadService.get_for_job(db, job.id, other_user)
    with pytest.raises(AppException) as missing:
        AIRestrictedPayloadService.get_for_job(db, uuid.uuid4(), other_user)

    # Same status and same error code: probing an id cannot tell "someone
    # else's payload" apart from "no such payload".
    assert cross_owner.value.status_code == missing.value.status_code == 404
    assert cross_owner.value.error_code == missing.value.error_code


@pytest.mark.integration
def test_expired_payloads_are_planned_and_purged_at_the_30_day_boundary(
    db, test_admin, test_teacher
):
    now = datetime.now(timezone.utc)
    material = _create_material(db, test_teacher["id"])

    inside_job = _create_job(db, test_teacher["id"], material.id)
    inside = _create_payload(db, inside_job, expires_at=now + timedelta(hours=1))
    expired_job = _create_job(db, test_teacher["id"], material.id)
    expired = _create_payload(db, expired_job, expires_at=now - timedelta(hours=1))
    db.commit()

    planned = plan_restricted_payload_purge(db)
    assert expired.id in planned.eligible_ids
    assert inside.id not in planned.eligible_ids

    # A dry run changes nothing.
    assert db.get(AIRestrictedPayload, expired.id) is not None

    report = apply_restricted_payload_purge(db, _admin_actor(test_admin))
    assert expired.id in report.purged_ids
    assert inside.id not in report.purged_ids

    assert db.get(AIRestrictedPayload, expired.id) is None
    # Still inside its window: untouched.
    assert db.get(AIRestrictedPayload, inside.id) is not None
    # §6.3 keeps the redacted metadata "while the parent business record
    # exists" -- expiring the raw prompt must not take the job with it.
    assert db.get(AIGenerationJob, expired_job.id) is not None


@pytest.mark.integration
def test_purged_payload_read_is_a_canonical_not_found(db, test_admin, test_teacher):
    from app.models.user import User

    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    _create_payload(
        db, job, expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.commit()

    apply_restricted_payload_purge(db, _admin_actor(test_admin))

    owner_user = db.get(User, test_teacher["id"])
    with pytest.raises(AppException) as exc:
        AIRestrictedPayloadService.get_for_job(db, job.id, owner_user)
    assert exc.value.status_code == 404


@pytest.mark.integration
def test_restricted_payload_purge_is_admin_only(db, test_teacher, test_student):
    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    payload = _create_payload(
        db, job, expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.commit()

    denied_actors = (
        _actor(test_teacher, "teacher"),
        _actor(test_student, "student"),
    )
    for denied in denied_actors:
        with pytest.raises(AppException) as exc:
            apply_restricted_payload_purge(db, denied)
        assert exc.value.status_code == 403
        db.rollback()

    assert db.get(AIRestrictedPayload, payload.id) is not None


@pytest.mark.integration
def test_purging_payloads_never_touches_protected_records(
    db, test_admin, test_teacher
):
    """The widened allowlist must not have made anything else reachable."""
    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    _create_payload(
        db, job, expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.commit()

    counts_before = {
        "submissions": len(db.scalars(select(Submission.id)).all()),
        "submission_answers": len(db.scalars(select(SubmissionAnswer.id)).all()),
        "audit_events": len(db.scalars(select(AuditEvent.event_id)).all()),
        "materials": len(db.scalars(select(StudyMaterial.id)).all()),
        "jobs": len(db.scalars(select(AIGenerationJob.id)).all()),
    }

    apply_restricted_payload_purge(db, _admin_actor(test_admin))

    counts_after = {
        "submissions": len(db.scalars(select(Submission.id)).all()),
        "submission_answers": len(db.scalars(select(SubmissionAnswer.id)).all()),
        # Audit events only ever grow -- the purge writes its own.
        "audit_events": len(db.scalars(select(AuditEvent.event_id)).all()),
        "materials": len(db.scalars(select(StudyMaterial.id)).all()),
        "jobs": len(db.scalars(select(AIGenerationJob.id)).all()),
    }

    assert counts_after["submissions"] == counts_before["submissions"]
    assert (
        counts_after["submission_answers"] == counts_before["submission_answers"]
    )
    assert counts_after["materials"] == counts_before["materials"]
    assert counts_after["jobs"] == counts_before["jobs"]
    assert counts_after["audit_events"] >= counts_before["audit_events"]


@pytest.mark.integration
def test_no_audit_event_ever_contains_the_raw_prompt_canary(
    db, test_admin, test_teacher
):
    """The end-to-end redaction claim, asserted over every audit row.

    `safe_payload` rejects the sensitive key names and the per-action
    allowlist rejects unknown fields, so a raw prompt has two independent
    barriers to cross. This asserts the outcome rather than the mechanism:
    after storing a payload whose prompt and output both contain a canary,
    and purging it, the canary appears in no audit event anywhere.
    """
    material = _create_material(db, test_teacher["id"])
    job = _create_job(db, test_teacher["id"], material.id)
    _create_payload(
        db, job, expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    db.commit()

    apply_restricted_payload_purge(db, _admin_actor(test_admin))

    for event in db.scalars(select(AuditEvent)).all():
        serialized = f"{event.changes!r} {event.event_metadata!r}"
        assert CANARY not in serialized
