from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from app.models.material import StudyMaterial
from app.models.document_chunk import DocumentChunk
from app.core.exceptions import AppException
import json

from app.ai import default_provider
from app.ai.model_policy import ModelUseCase, resolve_model_config
from app.ai.prompts import chat_system_v1
from app.ai.provider import AIProvider, AIProviderError, GenerateRequest
from app.core.security_guardrails import (
    detect_prompt_injection,
    sanitize_user_message,
    validate_messages,
    sanitize_error,
)
from app.core.permissions import Permission
from app.models.user import User
from app.services.authorization_service import AuthorizationService

class AiStudioService:
    @staticmethod
    def authorize_material(
        db: Session,
        material_id: UUID,
        current_user: User,
    ) -> StudyMaterial:
        material = db.scalar(
            AuthorizationService.scope_owned_statement(
                select(StudyMaterial),
                current_user,
                Permission.READ_OWNED_CONTENT,
                StudyMaterial.uploader_id,
            ).where(StudyMaterial.id == material_id)
        )
        if material is None:
            raise AppException(status_code=404, error_code="MATERIAL_NOT_FOUND")
        return material

    @staticmethod
    def process_document(
        db: Session,
        material_id: UUID,
        current_user: User,
    ):
        material = AiStudioService.authorize_material(
            db,
            material_id,
            current_user,
        )

        title = material.title or "document"
        chunks_text = [f"{title} - chunk 1", f"{title} - chunk 2"]

        mock_embedding = [0.1] * 1536

        for content in chunks_text:
            chunk = DocumentChunk(
                material_id=material.id,
                content=content,
                embedding=mock_embedding
            )
            db.add(chunk)

        AuthorizationService.commit_with_admin_override(
            db,
            actor=current_user,
            permission=Permission.READ_OWNED_CONTENT,
            entity_type="study_material",
            entity_id=material.id,
            owner_id=material.uploader_id,
            operation="process",
        )
        return len(chunks_text)

    @staticmethod
    async def chat_generator(
        db: Session,
        material: StudyMaterial,
        messages: list,
        current_user: User,
        provider: AIProvider = default_provider,
    ):
        try:
            safe_messages = validate_messages(messages)
            if not safe_messages:
                yield f"data: {json.dumps({'error': 'INVALID_MESSAGE_FORMAT'})}\n\n"
                return

            last_user_msg = ""
            for msg in reversed(safe_messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break

            if detect_prompt_injection(last_user_msg):
                yield f"data: {json.dumps({'text': 'Tôi chỉ có thể hỗ trợ các câu hỏi liên quan đến giáo dục và tài liệu học tập. Vui lòng đặt câu hỏi phù hợp.'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            safe_query = sanitize_user_message(last_user_msg)

            chunks = db.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.material_id == material.id,
                    DocumentChunk.content.ilike(f"%{safe_query[:100]}%"),
                )
                .limit(3)
            ).all()
            if not chunks:
                chunks = db.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.material_id == material.id)
                    .order_by(DocumentChunk.id.desc())
                    .limit(3)
                ).all()

            AuthorizationService.commit_with_admin_override(
                db,
                actor=current_user,
                permission=Permission.READ_OWNED_CONTENT,
                entity_type="study_material",
                entity_id=material.id,
                owner_id=material.uploader_id,
                operation="generate",
            )

            context_text = "\n".join([c.content for c in chunks])

            system_prompt = {
                "role": "system",
                "content": chat_system_v1.render(context_text),
            }

            messages_with_system = [system_prompt] + safe_messages

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "draft_exam",
                        "description": "Draft an exam with various question types (Single Choice, Multiple Choice, Matching, Fill in Blank). Only call this when the user explicitly asks to create exam questions.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "questions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "enum": ["SINGLE_CHOICE", "MULTIPLE_CHOICE", "MATCHING", "FILL_IN_BLANK"]},
                                            "content": {"type": "string"},
                                            "points": {"type": "number"},
                                            "options": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "content": {"type": "string"},
                                                        "is_correct": {"type": "boolean"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "draft_flashcards",
                        "description": "Draft flashcards with terms and definitions from the document",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "topic_id": {"type": "string"},
                                "flashcards": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "term": {"type": "string"},
                                            "definition": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "draft_topic_brief",
                        "description": "Draft a topic brief summary in markdown",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "topic_id": {"type": "string"},
                                "content": {"type": "string", "description": "Markdown content"}
                            }
                        }
                    }
                }
            ]

            model_config = resolve_model_config(ModelUseCase.CHAT)
            request = GenerateRequest(
                messages=messages_with_system,
                model=model_config.model,
                tools=tools,
                max_tokens=2048,
            )

            async for stream_chunk in provider.stream(request):
                if stream_chunk.text:
                    yield f"data: {json.dumps({'text': stream_chunk.text})}\n\n"
                if stream_chunk.tool_call_deltas:
                    tc_data = []
                    for tc in stream_chunk.tool_call_deltas:
                        tc_data.append({
                            "index": tc.index,
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments,
                            }
                        })
                    yield f"data: {json.dumps({'tool_calls': tc_data})}\n\n"

        except AIProviderError as e:
            yield f"data: {json.dumps({'error': e.error_code})}\n\n"
        except Exception as e:
            safe_error_code = sanitize_error(e)
            yield f"data: {json.dumps({'error': safe_error_code})}\n\n"
