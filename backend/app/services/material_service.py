import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from typing import List, Optional
from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.orm import Session, selectinload
from openai import OpenAI
from fastapi import BackgroundTasks

from app.models.material import StudyMaterial
from app.models.document_chunk import DocumentChunk
from app.models.exam import Question, Option
from app.models.flashcard import FlashcardDeck, Flashcard, FlashcardProgress
from app.models.enums import QuestionType, DifficultyLevel
from app.models.topic import Topic
from app.models.topic_brief import TopicBrief

from app.schemas.material import (
    MaterialDetailResponse, GenerateQuestionsRequest, SaveQuestionsRequest,
    GenerateFlashcardsRequest, SaveFlashcardsRequest, SaveTopicBriefRequest
)

from app.core.exceptions import AppException
from app.core.config import settings
from app.core.file_storage import FileStorage, material_file_storage
from app.core.security_guardrails import validate_file_upload
from app.core.permissions import Permission, require_owner_scope, require_permission
from app.core.correlation import get_current_request_id, new_correlation_id
from app.db.soft_delete import is_restorable, soft_delete
from app.models.submission import SubmissionAnswer
from app.models.user import User
from app.services.authorization_service import AuthorizationService

ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=getattr(settings, "OPENROUTER_API_KEY", None) or "mock_key",
)

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

    @staticmethod
    def generate_questions(
        db: Session,
        material_id: UUID,
        request: GenerateQuestionsRequest,
        current_user: User,
    ):
        require_permission(current_user, Permission.CREATE_CONTENT)
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.material_id == material.id)
        ).all()
        if not chunks:
            raise AppException(status_code=422, error_code="NO_CHUNKS_FOUND", message="No document chunks found.")

        context_text = "\n\n".join([f"[Đoạn {i+1}]: {c.content}" for i, c in enumerate(chunks)])
        types_str = ", ".join(request.question_types)
        
        system_prompt = f"""Bạn là AI chuyên sinh câu hỏi giáo dục chất lượng cao bằng Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới để sinh câu hỏi. KHÔNG bịa đặt.

TÀI LIỆU:
{context_text}

Sinh {request.count} câu hỏi phân bổ trong các loại sau: {types_str}. Độ khó mong muốn: {request.difficulty}.
Với mỗi câu hỏi PHẢI bao gồm 'difficulty' (EASY, MEDIUM, hoặc HARD), 'source_reference' (trích dẫn đoạn nào của tài liệu) và 'explanation' (giải thích).

TRẢ VỀ DUY NHẤT MỘT JSON ARRAY HỢP LỆ (KHÔNG có text xung quanh), định dạng như sau:
[
  {{
    "type": "SINGLE_CHOICE",
    "difficulty": "MEDIUM",
    "content": "Câu hỏi 1 đáp án...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [
      {{"content": "A", "is_correct": true}},
      {{"content": "B", "is_correct": false}}
    ]
  }},
  {{
    "type": "MATCHING",
    "difficulty": "HARD",
    "content": "Ghép nối...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [],
    "metadata_json": {{"pairs": [{{"left": "Vế 1", "right": "Vế 2"}}]}}
  }},
  {{
    "type": "FILL_IN_BLANK",
    "difficulty": "EASY",
    "content": "Điền khuyết...",
    "points": 1,
    "source_reference": "...",
    "explanation": "...",
    "options": [],
    "metadata_json": {{"blanks": [{{"blank_index": 0, "acceptable_answers": ["đáp án 1", "đáp án 2"]}}]}}
  }}
]
"""
        try:
            response = ai_client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()

            match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                first_brace = content.find('{')
                first_bracket = content.find('[')
                start_idx = -1
                if first_brace != -1 and first_bracket != -1:
                    start_idx = min(first_brace, first_bracket)
                elif first_brace != -1:
                    start_idx = first_brace
                elif first_bracket != -1:
                    start_idx = first_bracket
                    
                if start_idx != -1:
                    if content[start_idx] == '{':
                        end_idx = content.rfind('}')
                    else:
                        end_idx = content.rfind(']')
                    
                    if end_idx != -1:
                        content = content[start_idx:end_idx+1]

            questions = json.loads(content)
            AuthorizationService.commit_with_admin_override(
                db,
                actor=current_user,
                permission=Permission.READ_OWNED_CONTENT,
                entity_type="study_material",
                entity_id=material.id,
                owner_id=material.uploader_id,
                operation="generate",
            )
            return {"questions": questions}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_questions(
        db: Session,
        material_id: UUID,
        request: SaveQuestionsRequest,
        current_user: User,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
        )
        if material.uploader_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")

        saved_ids = []
        for q in request.questions:
            try:
                q_type = QuestionType[q.type]
            except KeyError:
                q_type = QuestionType.MULTIPLE_CHOICE

            try:
                q_difficulty = DifficultyLevel[q.difficulty.upper() if q.difficulty else "MEDIUM"]
            except (KeyError, AttributeError):
                q_difficulty = DifficultyLevel.MEDIUM

            metadata = q.metadata_json or {}
            if q.source_reference:
                metadata["source_reference"] = q.source_reference
            if q.explanation:
                metadata["explanation"] = q.explanation

            question = Question(
                owner_id=material.uploader_id,
                material_id=material_id,
                question_type=q_type,
                difficulty=q_difficulty,
                content=q.content,
                points=q.points,
                is_ai_generated=True,
                metadata_json=metadata
            )
            db.add(question)
            db.flush()

            for opt in q.options:
                option = Option(
                    question_id=question.id,
                    content=opt.content,
                    is_correct=opt.is_correct
                )
                db.add(option)

            saved_ids.append(str(question.id))

        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.APPROVE_OWNED_AI_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            operation="create_child",
        )
        return {"saved_count": len(saved_ids), "question_ids": saved_ids}

    @staticmethod
    def generate_flashcards(
        db: Session,
        material_id: UUID,
        request: GenerateFlashcardsRequest,
        current_user: User,
    ):
        require_permission(current_user, Permission.CREATE_CONTENT)
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.material_id == material.id)
        ).all()
        if not chunks:
            raise AppException(status_code=422, error_code="NO_CHUNKS_FOUND")

        context_text = "\n\n".join([c.content for c in chunks])

        system_prompt = f"""Bạn là AI chuyên tóm tắt tài liệu giáo dục thành thẻ ghi nhớ (flashcard) Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới.

TÀI LIỆU:
{context_text}

Sinh {request.count} cặp flashcard dưới dạng JSON THUẦN TÚY (không markdown).
Với mỗi flashcard PHẢI bao gồm 'source_reference' (trích dẫn đoạn nào của tài liệu) và 'explanation' (giải thích thêm hoặc ví dụ mở rộng).
{{
  "flashcards": [
    {{
      "term": "Thuật ngữ hoặc khái niệm",
      "definition": "Định nghĩa hoặc giải thích chi tiết",
      "source_reference": "Trích đoạn từ tài liệu",
      "explanation": "Giải thích thêm ngữ cảnh hoặc ví dụ"
    }},
    ...
  ]
}}
"""
        try:
            response = ai_client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.5,
            )
            content = response.choices[0].message.content.strip()

            match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                first_brace = content.find('{')
                first_bracket = content.find('[')
                start_idx = -1
                if first_brace != -1 and first_bracket != -1:
                    start_idx = min(first_brace, first_bracket)
                elif first_brace != -1:
                    start_idx = first_brace
                elif first_bracket != -1:
                    start_idx = first_bracket
                    
                if start_idx != -1:
                    if content[start_idx] == '{':
                        end_idx = content.rfind('}')
                    else:
                        end_idx = content.rfind(']')
                    
                    if end_idx != -1:
                        content = content[start_idx:end_idx+1]

            data = json.loads(content)
            AuthorizationService.commit_with_admin_override(
                db,
                actor=current_user,
                permission=Permission.READ_OWNED_CONTENT,
                entity_type="study_material",
                entity_id=material.id,
                owner_id=material.uploader_id,
                operation="generate",
            )
            return {"flashcards": data.get("flashcards", [])}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=str(e))
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_flashcards(
        db: Session,
        material_id: UUID,
        request: SaveFlashcardsRequest,
        current_user: User,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
        )
        if material.uploader_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")

        topic_id = UUID(request.topic_id) if request.topic_id else material.topic_id
        if not topic_id:
            default_topic = MaterialService._get_or_create_default_topic(
                db,
                material.uploader_id,
            )
            topic_id = default_topic.id
            material.topic_id = topic_id
        MaterialService._require_topic_owner(
            db,
            topic_id,
            material.uploader_id,
        )

        deck = FlashcardDeck(
            topic_id=topic_id,
            material_id=material.id,
            title=request.title,
            description=f"Tự động sinh từ tài liệu: {material.title}"
        )
        db.add(deck)
        db.flush()

        for i, fc in enumerate(request.flashcards):
            flashcard = Flashcard(
                deck_id=deck.id,
                front_content=fc.term,
                back_content=fc.definition,
                order_index=i
            )
            db.add(flashcard)

        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.APPROVE_OWNED_AI_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            operation="create_child",
        )
        return {"deck_id": str(deck.id), "saved_count": len(request.flashcards)}

    @staticmethod
    def generate_topic_brief(
        db: Session,
        material_id: UUID,
        current_user: User,
    ):
        require_permission(current_user, Permission.CREATE_CONTENT)
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
        )
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.material_id == material.id)
        ).all()
        if not chunks:
            raise AppException(status_code=422, error_code="NO_CHUNKS_FOUND")

        context_text = "\n\n".join([c.content for c in chunks])

        system_prompt = f"""Bạn là AI chuyên tóm tắt tài liệu giáo dục thành Topic Brief (Dàn ý chủ đề) bằng Tiếng Việt.
Chỉ sử dụng thông tin từ TÀI LIỆU bên dưới.

TÀI LIỆU:
{context_text}

Sinh bản tóm tắt topic brief dưới dạng JSON THUẦN TÚY (không markdown).
{{
  "content": "Nội dung tóm tắt định dạng markdown..."
}}
"""
        try:
            response = ai_client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.5,
            )
            content = response.choices[0].message.content.strip()

            match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                first_brace = content.find('{')
                first_bracket = content.find('[')
                start_idx = -1
                if first_brace != -1 and first_bracket != -1:
                    start_idx = min(first_brace, first_bracket)
                elif first_brace != -1:
                    start_idx = first_brace
                elif first_bracket != -1:
                    start_idx = first_bracket
                    
                if start_idx != -1:
                    if content[start_idx] == '{':
                        end_idx = content.rfind('}')
                    else:
                        end_idx = content.rfind(']')
                    
                    if end_idx != -1:
                        content = content[start_idx:end_idx+1]

            data = json.loads(content)
            AuthorizationService.commit_with_admin_override(
                db,
                actor=current_user,
                permission=Permission.READ_OWNED_CONTENT,
                entity_type="study_material",
                entity_id=material.id,
                owner_id=material.uploader_id,
                operation="generate",
            )
            return {"content": data.get("content", "")}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=str(e))
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_topic_brief(
        db: Session,
        material_id: UUID,
        request: SaveTopicBriefRequest,
        current_user: User,
    ):
        material = MaterialService.get_owned_material(
            db,
            material_id,
            current_user,
            Permission.APPROVE_OWNED_AI_CONTENT,
        )
        if material.uploader_id is None:
            raise AppException(status_code=409, error_code="CONTENT_OWNER_REQUIRED")

        topic_id = UUID(request.topic_id) if request.topic_id else material.topic_id
        if not topic_id:
            default_topic = MaterialService._get_or_create_default_topic(
                db,
                material.uploader_id,
            )
            topic_id = default_topic.id
            material.topic_id = topic_id
        MaterialService._require_topic_owner(
            db,
            topic_id,
            material.uploader_id,
        )

        brief = TopicBrief(
            topic_id=topic_id,
            material_id=material.id,
            title=request.title,
            content=request.content,
            is_ai_generated=True
        )
        db.add(brief)
        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.APPROVE_OWNED_AI_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            operation="create_child",
        )
        return {"brief_id": str(brief.id), "message": "Bản tóm tắt đã được lưu."}
