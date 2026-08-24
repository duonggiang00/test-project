import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from typing import List, Optional
from pydantic import ValidationError
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session, selectinload
from fastapi import BackgroundTasks

from app.models.ai_generation import AIGenerationJob
from app.models.material import StudyMaterial
from app.models.document_chunk import DocumentChunk
from app.models.exam import Question, Option
from app.models.flashcard import FlashcardDeck, Flashcard, FlashcardProgress
from app.models.enums import QuestionType, DifficultyLevel
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief

from app.schemas.ai_generation import (
    FlashcardDraft,
    PublishJobRequest,
    QuestionDraft,
    UpdateDraftRequest,
)
from app.schemas.material import (
    MaterialDetailResponse, GenerateQuestionsRequest,
    GenerateFlashcardsRequest,
)

from app.ai import default_provider
from app.ai.cost_policy import estimate_cost
from app.ai.json_extraction import extract_json_payload
from app.ai.model_policy import ModelUseCase, resolve_model_config
from app.ai.prompts import (
    flashcard_generation_v1,
    prompt_version_label,
    question_generation_v1,
    topic_brief_generation_v1,
)
from app.ai.provider import AIProvider, AIProviderError, GenerateRequest
from app.core.exceptions import AppException
from app.core.file_storage import FileStorage, material_file_storage
from app.core.security_guardrails import validate_file_upload
from app.core.permissions import Permission, require_owner_scope, require_permission
from app.core.correlation import get_current_request_id, new_correlation_id
from app.db.soft_delete import is_restorable, soft_delete
from app.models.submission import SubmissionAnswer
from app.models.user import User
from app.services.ai_generation_service import AIGenerationService
from app.services.ai_restricted_payload_service import AIRestrictedPayloadService
from app.services.authorization_service import AuthorizationService

class MaterialService:
    @staticmethod
    def _owned_material_statement(current_user: User, permission: Permission):
        return AuthorizationService.scope_owned_statement(
            select(StudyMaterial),
            current_user,
            permission,
            StudyMaterial.uploader_id,
        )

    @staticmethod
    def get_owned_material(
        db: Session,
        material_id: UUID,
        current_user: User,
        permission: Permission = Permission.READ_OWNED_CONTENT,
        *,
        lock: bool = False,
    ) -> StudyMaterial:
        statement = MaterialService._owned_material_statement(
            current_user,
            permission,
        ).where(StudyMaterial.id == material_id)
        if lock:
            statement = statement.with_for_update()
        material = db.scalar(
            statement
        )
        if material is None:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")
        return material

    @staticmethod
    def _require_topic_owner(
        db: Session,
        topic_id: UUID | None,
        owner_id: UUID | None,
    ) -> None:
        if topic_id is None:
            return
        owner_predicate = (
            Topic.owner_id.is_(None)
            if owner_id is None
            else Topic.owner_id == owner_id
        )
        if db.scalar(
            select(Topic.id).where(Topic.id == topic_id, owner_predicate)
        ) is None:
            raise AppException(status_code=404, error_code="TOPIC_NOT_FOUND")

    @staticmethod
    def _get_or_create_default_topic(
        db: Session,
        owner_id: UUID,
    ) -> Topic:
        default_topic = db.scalar(
            select(Topic).where(
                Topic.owner_id == owner_id,
                Topic.name == "AI Workspace Drafts",
            )
        )
        if default_topic is None:
            default_topic = Topic(
                owner_id=owner_id,
                name="AI Workspace Drafts",
                description="Private drafts created from AI workspace materials",
            )
            db.add(default_topic)
            db.flush()
        return default_topic

    @staticmethod
    def get_all_materials(db: Session, current_user: User):
        return MaterialService._owned_material_statement(
            current_user,
            Permission.READ_OWNED_CONTENT,
        ).order_by(StudyMaterial.created_at.desc(), StudyMaterial.id)

    @staticmethod
    def upload_material(
        db: Session,
        current_user: User,
        filename: str,
        content_type: str | None,
        content: bytes,
        background_tasks: BackgroundTasks,
        topic_id: Optional[UUID] = None,
        storage: FileStorage = material_file_storage,
    ):
        require_permission(current_user, Permission.CREATE_CONTENT)
        MaterialService._require_topic_owner(db, topic_id, current_user.id)
        is_valid, error_code = validate_file_upload(filename, content_type, content)
        if not is_valid:
            raise AppException(status_code=422, error_code=error_code)

        safe_filename = filename
        file_path = storage.save(safe_filename, content)

        try:
            material = StudyMaterial(
                uploader_id=current_user.id,
                topic_id=topic_id,
                title=safe_filename,
                file_type=safe_filename.rsplit(".", 1)[-1].lower(),
                file_path=file_path,
                ai_status="pending"
            )
            db.add(material)
            db.flush()
            AuthorizationService.commit_with_audit(
                db,
                actor=current_user,
                entity_type="study_material",
                entity_id=material.id,
                owner_id=current_user.id,
                action="material.upload",
                metadata={"file_type": material.file_type},
            )
            db.refresh(material)
        except Exception:
            db.rollback()
            storage.delete(file_path)
            raise

        from app.services.ai_service import mock_process_document_and_generate_questions
        background_tasks.add_task(
            mock_process_document_and_generate_questions,
            str(material.id),
            str(current_user.id),
            get_current_request_id() or new_correlation_id(),
        )

        return material

    @staticmethod
    def get_ai_questions(
        db: Session,
        material_id: UUID,
        current_user: User,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        scope = require_owner_scope(current_user, Permission.READ_OWNED_CONTENT)
        statement = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.material_id == material.id)
        )
        if scope.scoped_owner_id is not None:
            statement = statement.where(Question.owner_id == material.uploader_id)
        return db.scalars(statement).all()

    @staticmethod
    def get_material_detail(
        db: Session,
        material_id: UUID,
        current_user: User,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.material_id == material.id)
        ).all()

        return MaterialDetailResponse(
            id=material.id,
            title=material.title,
            file_type=material.file_type,
            ai_status=material.ai_status,
            created_at=material.created_at,
            chunks=chunks
        )

    @staticmethod
    def get_material_download(
        db: Session,
        material_id: UUID,
        current_user: User,
        storage: FileStorage = material_file_storage,
    ) -> tuple[Path, str]:
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
            Permission.READ_OWNED_CONTENT,
        )
        try:
            path = storage.resolve_for_read(material.file_path)
        except (FileNotFoundError, ValueError) as exc:
            raise AppException(
                status_code=404,
                error_code="MATERIAL_FILE_NOT_FOUND",
            ) from exc
        return path, Path(material.title).name or "material"

    @staticmethod
    def delete_material(
        db: Session,
        material_id: UUID,
        current_user: User,
        cascade: bool = False,
        keep_assets: bool = False,
        storage: FileStorage = material_file_storage,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
            Permission.DELETE_OWNED_CONTENT,
            lock=True,
        )
        
        q_count = db.scalar(
            select(func.count(Question.id)).where(Question.material_id == material.id)
        ) or 0
        f_count = db.scalar(
            select(func.count(FlashcardDeck.id)).where(
                FlashcardDeck.material_id == material.id
            )
        ) or 0
        b_count = db.scalar(
            select(func.count(TopicBrief.id)).where(
                TopicBrief.material_id == material.id
            )
        ) or 0

        if (q_count > 0 or f_count > 0 or b_count > 0) and not cascade and not keep_assets:
            return {
                "require_cascade": True,
                "linked_counts": {
                    "questions": q_count,
                    "flashcard_decks": f_count,
                    "topic_briefs": b_count
                },
                "message": f"Tài liệu này đang được liên kết với {q_count} câu hỏi, {f_count} bộ flashcard, và {b_count} bản tóm tắt."
            }
        
        if cascade:
            list(
                db.scalars(
                    select(Question.id)
                    .where(Question.material_id == material.id)
                    .order_by(Question.id)
                    .with_for_update()
                ).all()
            )
            linked_deck_ids = list(
                db.scalars(
                    select(FlashcardDeck.id)
                    .where(FlashcardDeck.material_id == material.id)
                    .order_by(FlashcardDeck.id)
                    .with_for_update()
                ).all()
            )
            if linked_deck_ids:
                list(
                    db.scalars(
                        select(Flashcard.id)
                        .where(Flashcard.deck_id.in_(linked_deck_ids))
                        .order_by(Flashcard.id)
                        .with_for_update()
                    ).all()
                )
            list(
                db.scalars(
                    select(TopicBrief.id)
                    .where(TopicBrief.material_id == material.id)
                    .order_by(TopicBrief.id)
                    .with_for_update()
                ).all()
            )
            unsafe_link_exists = db.scalar(
                select(
                    exists(
                        select(Question.id)
                        .outerjoin(
                            SubmissionAnswer,
                            SubmissionAnswer.question_id == Question.id,
                        )
                        .where(
                            Question.material_id == material.id,
                            (
                                (Question.owner_id != material.uploader_id)
                                | Question.owner_id.is_(None)
                                | Question.exam_id.is_not(None)
                                | SubmissionAnswer.id.is_not(None)
                            ),
                        )
                    )
                    | exists(
                        select(FlashcardDeck.id)
                        .join(Topic, FlashcardDeck.topic_id == Topic.id)
                        .outerjoin(
                            Flashcard,
                            Flashcard.deck_id == FlashcardDeck.id,
                        )
                        .outerjoin(
                            FlashcardProgress,
                            FlashcardProgress.flashcard_id == Flashcard.id,
                        )
                        .where(
                            FlashcardDeck.material_id == material.id,
                            (
                                (Topic.owner_id != material.uploader_id)
                                | Topic.owner_id.is_(None)
                                | FlashcardProgress.id.is_not(None)
                            ),
                        )
                    )
                    | exists(
                        select(TopicBrief.id)
                        .join(Topic, TopicBrief.topic_id == Topic.id)
                        .where(
                            TopicBrief.material_id == material.id,
                            (
                                (Topic.owner_id != material.uploader_id)
                                | Topic.owner_id.is_(None)
                            ),
                        )
                    )
                )
            )
            if unsafe_link_exists:
                raise AppException(
                    status_code=409,
                    error_code="MATERIAL_CASCADE_BLOCKED_BY_RETAINED_RECORDS",
                )
            db.execute(
                update(Question)
                .where(Question.material_id == material.id)
                .values(
                    deleted_at=datetime.now(timezone.utc),
                    deleted_by_id=current_user.id,
                )
            )
            db.execute(
                delete(FlashcardDeck).where(
                    FlashcardDeck.material_id == material.id
                )
            )
            db.execute(
                delete(TopicBrief).where(TopicBrief.material_id == material.id)
            )

        soft_delete(material, current_user.id)
        AuthorizationService.commit_with_audit(
            db,
            actor=current_user,
            permission=Permission.DELETE_OWNED_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            operation="delete",
            action="material.delete",
            metadata={"cascade": cascade},
        )

        # Deliberately does not touch the file in `storage`: this is a soft
        # delete with a 30-day recovery window (DATA-003/004), so the file
        # must stay recoverable in active storage until either an owner/admin
        # restores it (`restore_material`, download works again immediately)
        # or `purge_service.apply_purge` quarantines and permanently removes
        # it once the material is past the window. Deleting the file here
        # would silently break restore -- the metadata row would come back
        # but the download would 404 forever.
        return {"message": "Material and associated assets deleted successfully" if cascade else "Material deleted successfully"}

    @staticmethod
    def restore_material(
        db: Session,
        material_id: UUID,
        current_user: User,
    ) -> StudyMaterial:
        material = db.scalar(
            MaterialService._owned_material_statement(
                current_user,
                Permission.RESTORE_OWNED_CONTENT,
            )
            .where(
                StudyMaterial.id == material_id,
                StudyMaterial.deleted_at.is_not(None),
            )
            .execution_options(include_deleted=True)
            .with_for_update()
        )
        if material is None:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")

        if not is_restorable(material.deleted_at):
            raise AppException(
                status_code=409,
                error_code="MATERIAL_RESTORE_WINDOW_EXPIRED",
            )

        deleted_at_before = material.deleted_at
        material.deleted_at = None
        material.deleted_by_id = None

        AuthorizationService.commit_restore(
            db,
            actor=current_user,
            permission=Permission.RESTORE_OWNED_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            deleted_at_before=deleted_at_before,
        )
        db.refresh(material)
        return material

    # ------------------------------------------------------------------
    # AI generation (AI-002)
    #
    # Every `generate_*` below produces a *reviewable draft*, never live
    # content. The single path from a draft into `Question`/`Flashcard`/
    # `TopicBrief` is `publish_job`, which the ALLOWED_TRANSITIONS allowlist
    # only reaches from `approved`. The former `save_*` methods -- which
    # wrote those tables directly from a request body with no recorded
    # reviewer -- are gone precisely because they were a second path.
    # ------------------------------------------------------------------

    @staticmethod
    def _generation_context(
        db: Session,
        material_id: UUID,
        current_user: User,
    ) -> tuple[StudyMaterial, List[DocumentChunk]]:
        """Authorize, load the material, and fetch its prompt context."""
        require_permission(current_user, Permission.CREATE_CONTENT)
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        if material.uploader_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.material_id == material.id)
        ).all()
        if not chunks:
            raise AppException(status_code=422, error_code="NO_CHUNKS_FOUND")
        return material, chunks

    @staticmethod
    def _context_source_ids(chunks) -> list[str]:
        """The §2.4 `context_source_ids` for a retrieval context.

        Chunks without an id are skipped rather than stringified: an audit
        event should name the sources it actually has, and a placeholder
        would both fail the audit contract's UUID check and misreport what
        the model was given.
        """
        return [str(chunk.id) for chunk in chunks if chunk.id is not None]

    @staticmethod
    def _run_generation_job(
        db: Session,
        material: StudyMaterial,
        current_user: User,
        *,
        use_case: str,
        prompt: str,
        prompt_module,
        context_source_ids: list[str],
        model_use_case: ModelUseCase,
        temperature: float,
        provider: AIProvider,
        build_draft,
    ) -> AIGenerationJob:
        """Drive `requested -> processing -> generated -> awaiting_review`.

        The provider round trip deliberately sits *between* two committed
        transactions rather than inside one, per the AI-001-009 change
        contract: "Provider calls occur outside long database transactions;
        request/completion transitions use separate atomic transactions."
        A slow or hanging model therefore never holds a row lock or an idle
        transaction open, and a crash mid-call leaves a durable `processing`
        job rather than a silently vanished request.

        Each committed transition carries the AI-003
        `ERROR_AND_AUDIT_CONTRACTS.md` §2.4 metadata that is knowable at
        that point: `processing` records what the call is about to do
        (prompt version, provider/model, context sources), `generated`
        adds what came back (token usage, estimated cost, latency) plus the
        id of the restricted row holding the raw prompt/output. The raw text
        itself never travels through the audit path -- only that id does.
        """
        job = AIGenerationService.create_job(
            db,
            owner_id=material.uploader_id,
            material_id=material.id,
            use_case=use_case,
        )
        model_config = resolve_model_config(model_use_case)
        call_metadata = {
            "prompt_version": prompt_version_label(prompt_module),
            "provider": model_config.provider,
            "model": model_config.model,
        }
        if context_source_ids:
            call_metadata["context_source_ids"] = context_source_ids

        AIGenerationService.commit_transition(
            db,
            job,
            "processing",
            actor=current_user,
            override_permission=Permission.READ_OWNED_CONTENT,
            override_entity_type="study_material",
            override_entity_id=material.id,
            override_operation="generate",
            audit_metadata=call_metadata,
        )

        try:
            result = provider.generate(
                GenerateRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_config.model,
                    temperature=temperature,
                )
            )
            draft = build_draft(extract_json_payload(result.text))
        except json.JSONDecodeError as exc:
            MaterialService._fail_generation_job(
                db, job, current_user, "AI_PARSE_ERROR"
            )
            raise AppException(
                status_code=500, error_code="AI_PARSE_ERROR"
            ) from exc
        except AIProviderError as exc:
            # `AIProviderError.error_code` is already sanitized by the
            # provider layer, so it is safe to persist verbatim.
            MaterialService._fail_generation_job(
                db, job, current_user, exc.error_code
            )
            raise AppException(
                status_code=500, error_code="AI_GENERATION_FAILED"
            ) from exc
        except Exception as exc:
            MaterialService._fail_generation_job(
                db, job, current_user, "AI_GENERATION_FAILED"
            )
            raise AppException(
                status_code=500, error_code="AI_GENERATION_FAILED"
            ) from exc

        # The rendered prompt and raw response land in restricted storage,
        # flushed into the same transaction that commits the `generated`
        # transition -- so an audit event can never name a payload row that
        # was never written, nor can a payload row exist with no audited
        # reason for its §6.3 retention clock to have started.
        payload = AIRestrictedPayloadService.store(
            db,
            job=job,
            rendered_prompt=prompt,
            raw_output=result.text,
        )
        AIGenerationService.commit_transition(
            db,
            job,
            "generated",
            actor=current_user,
            draft_payload=draft,
            audit_metadata={
                **call_metadata,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "estimated_cost": estimate_cost(
                    model=result.model,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                ),
                "latency_ms": round(result.latency_ms),
                "restricted_payload_id": str(payload.id),
            },
        )
        AIGenerationService.commit_transition(
            db,
            job,
            "awaiting_review",
            actor=current_user,
        )
        return job

    @staticmethod
    def _fail_generation_job(
        db: Session,
        job: AIGenerationJob,
        actor: User,
        failure_code: str,
    ) -> None:
        """Record a terminal `failed` transition for a job that never got a draft."""
        AIGenerationService.commit_transition(
            db,
            job,
            "failed",
            actor=actor,
            failure_code=failure_code[:64],
        )

    @staticmethod
    def _draft_response(job: AIGenerationJob, payload_key: str, empty):
        draft = job.draft_payload or {}
        return {
            "job_id": str(job.id),
            "status": job.status,
            payload_key: draft.get(payload_key, empty),
        }

    @staticmethod
    def generate_questions(
        db: Session,
        material_id: UUID,
        request: GenerateQuestionsRequest,
        current_user: User,
        provider: AIProvider = default_provider,
    ):
        material, chunks = MaterialService._generation_context(
            db, material_id, current_user
        )
        context_text = "\n\n".join(
            [f"[Đoạn {i+1}]: {c.content}" for i, c in enumerate(chunks)]
        )
        prompt = question_generation_v1.render(
            context_text=context_text,
            count=request.count,
            question_types=", ".join(request.question_types),
            difficulty=request.difficulty,
        )
        job = MaterialService._run_generation_job(
            db,
            material,
            current_user,
            use_case="question_generation",
            prompt=prompt,
            prompt_module=question_generation_v1,
            context_source_ids=MaterialService._context_source_ids(chunks),
            model_use_case=ModelUseCase.QUESTION_GENERATION,
            temperature=0.7,
            provider=provider,
            build_draft=lambda payload: {"questions": payload},
        )
        return MaterialService._draft_response(job, "questions", [])

    @staticmethod
    def generate_flashcards(
        db: Session,
        material_id: UUID,
        request: GenerateFlashcardsRequest,
        current_user: User,
        provider: AIProvider = default_provider,
    ):
        material, chunks = MaterialService._generation_context(
            db, material_id, current_user
        )
        prompt = flashcard_generation_v1.render(
            context_text="\n\n".join([c.content for c in chunks]),
            count=request.count,
        )
        job = MaterialService._run_generation_job(
            db,
            material,
            current_user,
            use_case="flashcard_generation",
            prompt=prompt,
            prompt_module=flashcard_generation_v1,
            context_source_ids=MaterialService._context_source_ids(chunks),
            model_use_case=ModelUseCase.FLASHCARD_GENERATION,
            temperature=0.5,
            provider=provider,
            build_draft=lambda payload: {
                "flashcards": payload.get("flashcards", [])
            },
        )
        return MaterialService._draft_response(job, "flashcards", [])

    @staticmethod
    def generate_topic_brief(
        db: Session,
        material_id: UUID,
        current_user: User,
        provider: AIProvider = default_provider,
    ):
        material, chunks = MaterialService._generation_context(
            db, material_id, current_user
        )
        prompt = topic_brief_generation_v1.render(
            context_text="\n\n".join([c.content for c in chunks])
        )
        job = MaterialService._run_generation_job(
            db,
            material,
            current_user,
            use_case="topic_brief_generation",
            prompt=prompt,
            prompt_module=topic_brief_generation_v1,
            context_source_ids=MaterialService._context_source_ids(chunks),
            model_use_case=ModelUseCase.TOPIC_BRIEF_GENERATION,
            temperature=0.5,
            provider=provider,
            build_draft=lambda payload: {
                "content": payload.get("content", ""),
                "title": payload.get("title"),
            },
        )
        return MaterialService._draft_response(job, "content", "")

    # ------------------------------------------------------------------
    # Review decisions (AI-002)
    # ------------------------------------------------------------------

    @staticmethod
    def list_generation_jobs(
        db: Session,
        current_user: User,
        *,
        status: str | None = None,
        material_id: UUID | None = None,
    ):
        return AIGenerationService.list_jobs_statement(
            current_user,
            status=status,
            material_id=material_id,
        )

    @staticmethod
    def get_generation_job(
        db: Session,
        job_id: UUID,
        current_user: User,
    ) -> AIGenerationJob:
        return AIGenerationService.get_job_for_review(db, job_id, current_user)

    # Target status -> the audit vocabulary's name for the decision.
    _REVIEW_OPERATIONS = {"approved": "approve", "rejected": "reject"}

    @staticmethod
    def _review_decision(
        db: Session,
        job_id: UUID,
        current_user: User,
        target_status: str,
        expected_version: int | None,
    ) -> AIGenerationJob:
        job = AIGenerationService.get_job_for_review(
            db, job_id, current_user, lock=True
        )
        try:
            AIGenerationService.commit_transition(
                db,
                job,
                target_status,
                actor=current_user,
                expected_version=expected_version,
                override_permission=Permission.APPROVE_OWNED_AI_CONTENT,
                override_operation=MaterialService._REVIEW_OPERATIONS[
                    target_status
                ],
                # §2.4's reviewer/outcome pair. `reviewer_id` is the acting
                # user, which `transition` has just written onto the job for
                # the same reason: it is never inferred from the owner.
                audit_metadata={
                    "reviewer_id": str(current_user.id),
                    "review_outcome": target_status,
                },
            )
        except Exception:
            # Release the row lock taken by `get_job_for_review(lock=True)`
            # instead of leaving the request's transaction open behind a
            # refused decision.
            db.rollback()
            raise
        return job

    @staticmethod
    def approve_generation_job(
        db: Session,
        job_id: UUID,
        current_user: User,
        expected_version: int | None = None,
    ) -> AIGenerationJob:
        return MaterialService._review_decision(
            db, job_id, current_user, "approved", expected_version
        )

    @staticmethod
    def reject_generation_job(
        db: Session,
        job_id: UUID,
        current_user: User,
        expected_version: int | None = None,
    ) -> AIGenerationJob:
        return MaterialService._review_decision(
            db, job_id, current_user, "rejected", expected_version
        )

    @staticmethod
    def update_generation_job_draft(
        db: Session,
        job_id: UUID,
        current_user: User,
        request: UpdateDraftRequest,
    ) -> AIGenerationJob:
        """A reviewer reshapes a draft -- edit, clear, or add items -- before
        deciding on it.

        Only reachable while the job is `awaiting_review`:
        `AIGenerationService.commit_draft_edit` refuses any other status, so
        an approved draft can never be edited out from under its approval,
        and `publish` still reads exclusively from whatever `draft_payload`
        was last saved here.
        """
        job = AIGenerationService.get_job_for_review(
            db, job_id, current_user, lock=True
        )
        if job.use_case == "question_generation":
            if request.questions is None:
                raise AppException(
                    status_code=422, error_code="AI_DRAFT_FIELD_MISMATCH"
                )
            draft_payload = {
                "questions": [q.model_dump() for q in request.questions]
            }
        elif job.use_case == "flashcard_generation":
            if request.flashcards is None:
                raise AppException(
                    status_code=422, error_code="AI_DRAFT_FIELD_MISMATCH"
                )
            draft_payload = {
                "flashcards": [f.model_dump() for f in request.flashcards]
            }
        elif job.use_case == "topic_brief_generation":
            if request.content is None:
                raise AppException(
                    status_code=422, error_code="AI_DRAFT_FIELD_MISMATCH"
                )
            draft_payload = {"content": request.content, "title": request.title}
        else:
            raise AppException(
                status_code=422, error_code="AI_DRAFT_FIELD_MISMATCH"
            )

        try:
            return AIGenerationService.commit_draft_edit(
                db,
                job,
                actor=current_user,
                draft_payload=draft_payload,
                expected_version=request.expected_version,
            )
        except Exception:
            # Release the row lock taken by `get_job_for_review(lock=True)`
            # instead of leaving the request's transaction open behind a
            # refused edit, matching `_review_decision`'s same handling.
            db.rollback()
            raise

    # ------------------------------------------------------------------
    # Publication (AI-002) -- the only writer of live AI content
    # ------------------------------------------------------------------

    @staticmethod
    def publish_generation_job(
        db: Session,
        job_id: UUID,
        current_user: User,
        request: PublishJobRequest | None = None,
    ):
        """Write an approved draft into the live tables, once.

        Reachable only from `approved`: the allowlist has no
        `generated -> published` pair and no `published -> published` pair,
        so an unreviewed job and an already-published job are both refused
        with `AI_JOB_INVALID_TRANSITION` -- there is no separate
        "already published" guard to keep in sync with the state machine.
        The rows and the `published` transition share one transaction, so a
        failure part-way through publishes nothing.
        """
        request = request or PublishJobRequest()
        job = AIGenerationService.get_job_for_review(
            db, job_id, current_user, lock=True
        )
        # Both guards run before a single row is built. Deferring the version
        # check to `commit_transition` would leave the rejected publish's rows
        # pending in the session, where the next commit on that session would
        # flush them -- a stale reviewer would publish after all.
        AIGenerationService.assert_transition_allowed(job.status, "published")
        if (
            request.expected_version is not None
            and job.version != request.expected_version
        ):
            raise AppException(
                status_code=409, error_code="AI_JOB_VERSION_CONFLICT"
            )

        try:
            material = db.scalar(
                select(StudyMaterial).where(StudyMaterial.id == job.material_id)
            )
            if material is None or material.uploader_id is None:
                raise AppException(
                    status_code=404, error_code="MATERIAL_NOT_FOUND"
                )

            publisher_name = MaterialService._PUBLISHERS.get(job.use_case)
            if publisher_name is None:
                raise AppException(
                    status_code=409,
                    error_code="AI_JOB_USE_CASE_NOT_PUBLISHABLE",
                )
            published = getattr(MaterialService, publisher_name)(
                db, job, material, request
            )

            AIGenerationService.commit_transition(
                db,
                job,
                "published",
                actor=current_user,
                expected_version=request.expected_version,
                override_permission=Permission.APPROVE_OWNED_AI_CONTENT,
                override_operation="publish",
            )
        except Exception:
            # Anything that fails after the first `db.add` must take the
            # whole publish with it: a half-written deck plus a job still
            # marked `approved` is worse than nothing written at all.
            db.rollback()
            raise
        return {"job_id": str(job.id), "status": "published", **published}

    @staticmethod
    def _validated_drafts(job: AIGenerationJob, key: str, model):
        raw = (job.draft_payload or {}).get(key) or []
        if not isinstance(raw, list):
            raise AppException(status_code=422, error_code="AI_DRAFT_INVALID")
        try:
            return [model.model_validate(item) for item in raw]
        except ValidationError as exc:
            raise AppException(
                status_code=422, error_code="AI_DRAFT_INVALID"
            ) from exc

    @staticmethod
    def _resolve_publish_topic(
        db: Session,
        material: StudyMaterial,
        request: PublishJobRequest,
    ) -> UUID:
        topic_id = UUID(request.topic_id) if request.topic_id else material.topic_id
        if not topic_id:
            default_topic = MaterialService._get_or_create_default_topic(
                db,
                material.uploader_id,
            )
            topic_id = default_topic.id
            material.topic_id = topic_id
        MaterialService._require_topic_owner(db, topic_id, material.uploader_id)
        return topic_id

    @staticmethod
    def _publish_questions(
        db: Session,
        job: AIGenerationJob,
        material: StudyMaterial,
        request: PublishJobRequest,
    ):
        drafts = MaterialService._validated_drafts(
            job, "questions", QuestionDraft
        )
        saved_ids = []
        for draft in drafts:
            try:
                q_type = QuestionType[draft.type]
            except KeyError:
                q_type = QuestionType.MULTIPLE_CHOICE
            try:
                q_difficulty = DifficultyLevel[
                    draft.difficulty.upper() if draft.difficulty else "MEDIUM"
                ]
            except (KeyError, AttributeError):
                q_difficulty = DifficultyLevel.MEDIUM

            metadata = dict(draft.metadata_json or {})
            if draft.source_reference:
                metadata["source_reference"] = draft.source_reference
            if draft.explanation:
                metadata["explanation"] = draft.explanation

            question = Question(
                owner_id=material.uploader_id,
                material_id=material.id,
                question_type=q_type,
                difficulty=q_difficulty,
                content=draft.content,
                points=draft.points,
                is_ai_generated=True,
                metadata_json=metadata,
            )
            db.add(question)
            db.flush()
            for opt in draft.options:
                db.add(
                    Option(
                        question_id=question.id,
                        content=opt.content,
                        is_correct=opt.is_correct,
                    )
                )
            saved_ids.append(str(question.id))
        return {"saved_count": len(saved_ids), "question_ids": saved_ids}

    @staticmethod
    def _publish_flashcards(
        db: Session,
        job: AIGenerationJob,
        material: StudyMaterial,
        request: PublishJobRequest,
    ):
        drafts = MaterialService._validated_drafts(
            job, "flashcards", FlashcardDraft
        )
        topic_id = MaterialService._resolve_publish_topic(db, material, request)
        deck = FlashcardDeck(
            topic_id=topic_id,
            material_id=material.id,
            title=request.title or f"Flashcards: {material.title}",
            description=f"Tự động sinh từ tài liệu: {material.title}",
        )
        db.add(deck)
        db.flush()
        for index, draft in enumerate(drafts):
            db.add(
                Flashcard(
                    deck_id=deck.id,
                    front_content=draft.term,
                    back_content=draft.definition,
                    order_index=index,
                )
            )
        return {"deck_id": str(deck.id), "saved_count": len(drafts)}

    @staticmethod
    def _publish_topic_brief(
        db: Session,
        job: AIGenerationJob,
        material: StudyMaterial,
        request: PublishJobRequest,
    ):
        draft = job.draft_payload or {}
        content = draft.get("content")
        if not content:
            raise AppException(status_code=422, error_code="AI_DRAFT_INVALID")
        topic_id = MaterialService._resolve_publish_topic(db, material, request)
        brief = TopicBrief(
            topic_id=topic_id,
            material_id=material.id,
            title=request.title or draft.get("title") or material.title,
            content=content,
            is_ai_generated=True,
        )
        db.add(brief)
        db.flush()
        return {"brief_id": str(brief.id)}

    # use_case -> publisher method name. Stored as names rather than the
    # functions themselves so the mapping resolves through the normal
    # descriptor protocol instead of holding raw `staticmethod` objects.
    _PUBLISHERS = {
        "question_generation": "_publish_questions",
        "flashcard_generation": "_publish_flashcards",
        "topic_brief_generation": "_publish_topic_brief",
    }
