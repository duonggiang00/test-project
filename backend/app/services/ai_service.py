import time
import logging
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.core.permissions import Permission, evaluate_owned_resource
from app.services.ai_generation_service import AIGenerationService
from app.services.authorization_service import AuthorizationService
from app.services.material_processing import extract_and_chunk_material
import os

logger = logging.getLogger(__name__)



def _park_draft_for_review(
    db,
    *,
    actor,
    material,
    use_case: str,
    draft_payload: dict,
    request_id: str,
    override_permission=None,
    override_entity_type: str | None = None,
    override_entity_id=None,
):
    """Create one generation job and drive it to `awaiting_review`.

    Shared by the background workers so both reach the review queue by the
    same route as the request-path flows: each transition is its own atomic
    transaction carrying exactly one audit event, and the job stops short of
    any publish.

    The `override_*` arguments ride only on the first transition, matching
    `MaterialService._run_generation_job`: a non-owning admin triggering
    generation produces exactly one `admin.override` event for the request,
    not one per state change.
    """
    job = AIGenerationService.create_job(
        db,
        owner_id=material.uploader_id,
        material_id=material.id,
        use_case=use_case,
    )
    AIGenerationService.commit_transition(
        db,
        job,
        "processing",
        actor=actor,
        request_id=request_id,
        override_permission=override_permission,
        override_entity_type=override_entity_type,
        override_entity_id=override_entity_id,
        override_operation="generate" if override_permission else None,
    )
    AIGenerationService.commit_transition(
        db,
        job,
        "generated",
        actor=actor,
        draft_payload=draft_payload,
        request_id=request_id,
    )
    AIGenerationService.commit_transition(
        db, job, "awaiting_review", actor=actor, request_id=request_id
    )
    return job


def mock_process_document_and_generate_questions(
    material_id: str,
    expected_owner_id: str,
    request_id: str,
):
    # Simulate processing time
    time.sleep(5)
    
    with SessionLocal() as db:
        material = db.scalar(
            select(StudyMaterial).where(
                StudyMaterial.id == UUID(material_id),
                StudyMaterial.uploader_id == UUID(expected_owner_id),
            )
        )
        if not material:
            return
            
        # 1. Process Document and Create Chunks
        try:
            content, chunks = extract_and_chunk_material(Path(material.file_path))
            for para in chunks:
                chunk = DocumentChunk(
                    material_id=material.id,
                    content=para,
                    embedding=[0.1] * 1536,
                )
                db.add(chunk)
            material.parsed_text = content
            db.commit()
        except Exception:
            logger.warning(
                "Background document processing failed request_id=%s",
                request_id,
            )
            material.ai_status = 'failed'
            db.commit()
            return
            
        # Mock generating questions.
        #
        # This used to `db.add(Question(...))` straight into the live table,
        # which made an upload an unreviewed publish: two AI-authored
        # questions appeared under the uploader's account with no approval,
        # no reviewer, and no way to reject them. The mock *content* is
        # unchanged; what changed is where it lands. It now becomes an
        # `AIGenerationJob` draft that stops at `awaiting_review`, so the
        # only route from here into `Question` is the same explicit publish
        # every other generation flow goes through.
        actor = db.get(User, material.uploader_id)
        if actor is None:
            material.ai_status = "failed"
            db.commit()
            return

        draft_payload = {
            "questions": [
                {
                    "type": "MULTIPLE_CHOICE",
                    "content": f"What is the main topic of {material.title}?",
                    "points": 1,
                    "options": [
                        {"content": "AI", "is_correct": True},
                        {"content": "Blockchain", "is_correct": False},
                    ],
                },
                {
                    "type": "MULTIPLE_CHOICE",
                    "content": "Which statement is true based on the document?",
                    "points": 1,
                    "options": [
                        {"content": "This is true", "is_correct": True},
                        {"content": "This is false", "is_correct": False},
                    ],
                },
            ]
        }

        job = AIGenerationService.create_job(
            db,
            owner_id=material.uploader_id,
            material_id=material.id,
            use_case="question_generation",
        )
        # Each transition is its own atomic transaction with exactly one
        # audit event, matching the request-path generation flow.
        AIGenerationService.commit_transition(
            db, job, "processing", actor=actor, request_id=request_id
        )
        AIGenerationService.commit_transition(
            db,
            job,
            "generated",
            actor=actor,
            draft_payload=draft_payload,
            request_id=request_id,
        )
        AIGenerationService.commit_transition(
            db, job, "awaiting_review", actor=actor, request_id=request_id
        )

        material.ai_status = "completed"
        db.commit()

def mock_generate_topic_kit(
    material_id: str,
    topic_id: str,
    expected_owner_id: str,
    actor_id: str,
    request_id: str,
):
    """
    Mock function to simulate AI generating a Topic Brief and Flashcards from a Study Material.
    """
    time.sleep(3) # Simulate AI processing time
    
    with SessionLocal() as db:
        owner_id = UUID(expected_owner_id)
        material = db.scalar(
            select(StudyMaterial).where(
                StudyMaterial.id == UUID(material_id),
                StudyMaterial.uploader_id == owner_id,
            )
        )
        topic = db.scalar(
            select(Topic).where(
                Topic.id == UUID(topic_id),
                Topic.owner_id == owner_id,
            )
        )
        actor = db.scalar(
            select(User)
            .where(User.id == UUID(actor_id))
            .with_for_update(read=True)
        )
        
        if not material or not topic or not actor:
            return
        if not evaluate_owned_resource(
            actor,
            Permission.UPDATE_OWNED_CONTENT,
            topic.owner_id,
        ).allowed:
            return

        # Mock generating a topic kit.
        #
        # This used to write straight into the live tables: it set
        # `topic.brief_content`/`brief_ai_generated` and added a
        # `FlashcardDeck` with its `Flashcard` rows, so calling
        # `POST /flashcards/ai/generate-topic-kit` published AI-authored
        # content to students with no approval, no reviewer, and no way to
        # reject it. `CANONICAL_PROJECT_SPEC.md` 9.2 names generated
        # flashcards and generated topic briefs as requiring human approval,
        # and ADR-0006's supersession clause makes automatic publishing a
        # decision needing a new ADR -- so the mock *content* is unchanged,
        # but it now stops at `awaiting_review` like every other flow.
        #
        # Two jobs rather than one: a brief and a deck are separately
        # reviewable and separately publishable, and splitting them here
        # reuses the existing `topic_brief_generation`/`flashcard_generation`
        # publishers unchanged instead of inventing a combined use case with
        # a third publish branch.
        brief_content = (
            f"# {topic.name}\n\nĐây là bài tóm tắt kiến thức được tạo "
            f"tự động bởi AI từ tài liệu: **{material.title}**.\n\n"
            "## 1. Khái niệm cơ bản\nNội dung khái niệm...\n\n"
            "## 2. Các điểm trọng tâm\n- Điểm 1\n- Điểm 2\n"
        )
        cards_data = [
            (
                "AI là gì?",
                "Trí tuệ nhân tạo (AI) là khả năng của máy tính bắt chước các "
                "chức năng nhận thức của con người.",
            ),
            (
                "Spaced Repetition là gì?",
                "Kỹ thuật ôn tập ngắt quãng giúp ghi nhớ dài hạn bằng cách tăng "
                "dần thời gian giữa các lần ôn tập.",
            ),
            (
                "Mô hình Dữ liệu (Data Model) là gì?",
                "Cách cấu trúc và tổ chức dữ liệu trong cơ sở dữ liệu.",
            ),
        ]

        _park_draft_for_review(
            db,
            actor=actor,
            material=material,
            use_case="topic_brief_generation",
            draft_payload={
                "content": brief_content,
                "title": f"Tóm tắt: {material.title}",
            },
            request_id=request_id,
            override_permission=Permission.UPDATE_OWNED_CONTENT,
            override_entity_type="topic",
            override_entity_id=topic.id,
        )
        _park_draft_for_review(
            db,
            actor=actor,
            material=material,
            use_case="flashcard_generation",
            draft_payload={
                "flashcards": [
                    {"front_content": front, "back_content": back}
                    for front, back in cards_data
                ]
            },
            request_id=request_id,
        )
