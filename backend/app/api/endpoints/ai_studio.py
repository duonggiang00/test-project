from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.ai import ProcessDocumentRequest, ProcessDocumentResponse
from app.schemas.ai_generation import (
    AIGenerationJobResponse,
    PublishJobRequest,
    ReviewDecisionRequest,
)
from app.core.security_guardrails import MAX_MESSAGES
from app.api.deps import get_current_active_teacher
from app.models.user import User
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.services.ai_studio_service import AiStudioService
from app.services.material_service import MaterialService

class ChatRequest(BaseModel):
    material_id: UUID
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
    chunks_created = AiStudioService.process_document(
        db,
        request.material_id,
        current_user,
    )
    return ProcessDocumentResponse(message="Processed successfully", chunks_created=chunks_created)

@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    material = AiStudioService.authorize_material(
        db,
        request.material_id,
        current_user,
    )
    return StreamingResponse(
        AiStudioService.chat_generator(
            db,
            material,
            request.messages,
            current_user,
        ),
        media_type="text/event-stream"
    )


# --------------------------------------------------------------------------
# AI generation review queue (AI-002).
#
# `publish` is the only route in the application that writes AI-generated
# Question/Flashcard/TopicBrief rows, and the transition allowlist only
# reaches `published` from `approved`.
# --------------------------------------------------------------------------

@router.get("/generation-jobs", response_model=Page[AIGenerationJobResponse])
def list_generation_jobs(
    status: Optional[str] = None,
    material_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return paginate(
        db,
        MaterialService.list_generation_jobs(
            db,
            current_user,
            status=status,
            material_id=material_id,
        ),
    )


@router.get(
    "/generation-jobs/{job_id}",
    response_model=AIGenerationJobResponse,
)
def get_generation_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return MaterialService.get_generation_job(db, job_id, current_user)


@router.post(
    "/generation-jobs/{job_id}/approve",
    response_model=AIGenerationJobResponse,
)
def approve_generation_job(
    job_id: UUID,
    request: ReviewDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return MaterialService.approve_generation_job(
        db,
        job_id,
        current_user,
        expected_version=(request or ReviewDecisionRequest()).expected_version,
    )


@router.post(
    "/generation-jobs/{job_id}/reject",
    response_model=AIGenerationJobResponse,
)
def reject_generation_job(
    job_id: UUID,
    request: ReviewDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return MaterialService.reject_generation_job(
        db,
        job_id,
        current_user,
        expected_version=(request or ReviewDecisionRequest()).expected_version,
    )


@router.post("/generation-jobs/{job_id}/publish")
def publish_generation_job(
    job_id: UUID,
    request: PublishJobRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return MaterialService.publish_generation_job(
        db,
        job_id,
        current_user,
        request,
    )
