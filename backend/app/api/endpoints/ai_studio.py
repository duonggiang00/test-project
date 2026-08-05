from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.ai import ProcessDocumentRequest, ProcessDocumentResponse
from app.core.security_guardrails import MAX_MESSAGES
from app.api.deps import get_current_active_teacher
from app.models.user import User
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any
from fastapi.responses import StreamingResponse

from app.services.ai_studio_service import AiStudioService

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]

    @field_validator("messages")
    @classmethod
    def validate_message_count(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(v) > MAX_MESSAGES * 2:
            raise ValueError(f"Too many messages. Maximum allowed: {MAX_MESSAGES * 2}")
        return v

router = APIRouter()

@router.post("/process-document", response_model=ProcessDocumentResponse)
def process_document(
    request: ProcessDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    chunks_created = AiStudioService.process_document(db, request.material_id)
    return ProcessDocumentResponse(message="Processed successfully", chunks_created=chunks_created)

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return StreamingResponse(
        AiStudioService.chat_generator(db, request.messages),
        media_type="text/event-stream"
    )
