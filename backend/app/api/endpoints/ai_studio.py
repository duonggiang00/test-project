from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.ai import ChatRequest
from app.schemas.ai_generation import (
    AIGenerationJobResponse,
    PublishJobRequest,
    ReviewDecisionRequest,
    UpdateDraftRequest,
)
from app.core.config import settings
from app.core.exceptions import AppException
from app.api.deps import get_current_active_teacher
from app.models.user import User
from typing import Optional
from uuid import UUID
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.services.ai_studio_service import AiStudioService
from app.services.material_service import MaterialService

router = APIRouter()


def require_rag_enabled() -> None:
    """Fail closed before authentication, retrieval, or provider access."""
    if not settings.RAG_ENABLED:
        raise AppException(
            status_code=404,
            error_code="FEATURE_NOT_AVAILABLE",
        )


@router.post("/chat", dependencies=[Depends(require_rag_enabled)])
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
            [message.model_dump() for message in request.messages],
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


@router.patch(
    "/generation-jobs/{job_id}/draft",
    response_model=AIGenerationJobResponse,
)
def update_generation_job_draft(
    job_id: UUID,
    request: UpdateDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    return MaterialService.update_generation_job_draft(
        db,
        job_id,
        current_user,
        request,
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
