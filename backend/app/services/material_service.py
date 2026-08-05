import json
import re
from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from openai import OpenAI
from fastapi import BackgroundTasks

from app.models.material import StudyMaterial
from app.models.document_chunk import DocumentChunk
from app.models.exam import Question, Option
from app.models.flashcard import FlashcardDeck, Flashcard
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

ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=getattr(settings, "OPENROUTER_API_KEY", None) or "mock_key",
)

class MaterialService:
    @staticmethod
    def get_all_materials(db: Session):
        return db.query(StudyMaterial)

    @staticmethod
    def upload_material(
        db: Session,
        current_user_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
        background_tasks: BackgroundTasks,
        topic_id: Optional[UUID] = None,
        storage: FileStorage = material_file_storage,
    ):
        is_valid, error_code = validate_file_upload(filename, content_type, content)
        if not is_valid:
            raise AppException(status_code=422, error_code=error_code)

        safe_filename = filename
        file_path = storage.save(safe_filename, content)

        try:
            material = StudyMaterial(
                uploader_id=current_user_id,
                topic_id=topic_id,
                title=safe_filename,
                file_type=safe_filename.rsplit(".", 1)[-1].lower(),
                file_path=file_path,
                ai_status="pending"
            )
            db.add(material)
            db.commit()
            db.refresh(material)
        except Exception:
            db.rollback()
            storage.delete(file_path)
            raise

        from app.services.ai_service import mock_process_document_and_generate_questions
        background_tasks.add_task(mock_process_document_and_generate_questions, material.id)

        return material

    @staticmethod
    def get_ai_questions(db: Session, material_id: UUID):
        return db.query(Question).options(selectinload(Question.options)).filter(Question.material_id == material_id).all()

    @staticmethod
    def get_material_detail(db: Session, material_id: UUID):
        material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not material:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND", message="Material not found")

        chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).all()

        return MaterialDetailResponse(
            id=material.id,
            title=material.title,
            file_type=material.file_type,
            file_path=material.file_path,
            ai_status=material.ai_status,
            created_at=material.created_at,
            chunks=chunks
        )

    @staticmethod
    def delete_material(
        db: Session,
        material_id: UUID,
        cascade: bool = False,
        keep_assets: bool = False,
        storage: FileStorage = material_file_storage,
    ):
        material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not material:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND", message="Material not found")
        
        q_count = db.query(Question).filter(Question.material_id == material_id).count()
        f_count = db.query(FlashcardDeck).filter(FlashcardDeck.material_id == material_id).count()
        b_count = db.query(TopicBrief).filter(TopicBrief.material_id == material_id).count()

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
            db.query(Question).filter(Question.material_id == material_id).delete(synchronize_session=False)
            db.query(FlashcardDeck).filter(FlashcardDeck.material_id == material_id).delete(synchronize_session=False)
            db.query(TopicBrief).filter(TopicBrief.material_id == material_id).delete(synchronize_session=False)

        file_path = material.file_path

        db.delete(material)
        db.commit()

        if file_path:
            storage.delete(file_path)

        return {"message": "Material and associated assets deleted successfully" if cascade else "Material deleted successfully"}

    @staticmethod
    def generate_questions(db: Session, material_id: UUID, request: GenerateQuestionsRequest):
        chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).all()
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
            return {"questions": questions}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=f"Failed to parse AI response as JSON: {str(e)}")
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_questions(db: Session, material_id: UUID, request: SaveQuestionsRequest):
        material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not material:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")

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

        db.commit()
        return {"saved_count": len(saved_ids), "question_ids": saved_ids}

    @staticmethod
    def generate_flashcards(db: Session, material_id: UUID, request: GenerateFlashcardsRequest):
        chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).all()
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
            return {"flashcards": data.get("flashcards", [])}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=str(e))
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_flashcards(db: Session, material_id: UUID, request: SaveFlashcardsRequest):
        material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not material:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")

        topic_id = UUID(request.topic_id) if request.topic_id else material.topic_id
        if not topic_id:
            default_topic = db.query(Topic).filter(Topic.name == "AI Workspace Drafts").first()
            if not default_topic:
                default_topic = Topic(name="AI Workspace Drafts", description="Tự động tạo để lưu trữ dữ liệu AI")
                db.add(default_topic)
                db.commit()
                db.refresh(default_topic)
            topic_id = default_topic.id
            material.topic_id = topic_id
            db.commit()

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

        db.commit()
        return {"deck_id": str(deck.id), "saved_count": len(request.flashcards)}

    @staticmethod
    def generate_topic_brief(db: Session, material_id: UUID):
        chunks = db.query(DocumentChunk).filter(DocumentChunk.material_id == material_id).all()
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
            return {"content": data.get("content", "")}
        except json.JSONDecodeError as e:
            raise AppException(status_code=500, error_code="AI_PARSE_ERROR", message=str(e))
        except Exception as e:
            raise AppException(status_code=500, error_code="AI_GENERATION_FAILED", message=str(e))

    @staticmethod
    def save_topic_brief(db: Session, material_id: UUID, request: SaveTopicBriefRequest):
        material = db.query(StudyMaterial).filter(StudyMaterial.id == material_id).first()
        if not material:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")

        topic_id = UUID(request.topic_id) if request.topic_id else material.topic_id
        if not topic_id:
            default_topic = db.query(Topic).filter(Topic.name == "AI Workspace Drafts").first()
            if not default_topic:
                default_topic = Topic(name="AI Workspace Drafts", description="Tự động tạo để lưu trữ dữ liệu AI")
                db.add(default_topic)
                db.commit()
                db.refresh(default_topic)
            topic_id = default_topic.id
            material.topic_id = topic_id
            db.commit()

        brief = TopicBrief(
            topic_id=topic_id,
            material_id=material.id,
            title=request.title,
            content=request.content,
            is_ai_generated=True
        )
        db.add(brief)
        db.commit()
        return {"brief_id": str(brief.id), "message": "Bản tóm tắt đã được lưu."}
