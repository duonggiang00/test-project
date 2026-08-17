from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.user import User
from app.schemas.material import (
    MaterialResponse, MaterialDetailResponse,
    GenerateQuestionsRequest, SaveQuestionsRequest,
    GenerateFlashcardsRequest, SaveFlashcardsRequest,
    SaveTopicBriefRequest
)
from app.schemas.question import QuestionResponse
from app.api.deps import get_current_active_teacher
from app.services.material_service import MaterialService
from app.core.security_guardrails import MAX_FILE_SIZE_BYTES
from app.core.exceptions import AppException

router = APIRouter()

@router.get("", response_model=Page[MaterialResponse])
def get_all_materials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return paginate(db, MaterialService.get_all_materials(db, current_user))

@router.post("/upload", response_model=MaterialResponse)
def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topic_id: Optional[UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    content = file.file.read(MAX_FILE_SIZE_BYTES + 1)
    return MaterialService.upload_material(
        db=db,
        current_user=current_user,
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        background_tasks=background_tasks,
        topic_id=topic_id
    )

@router.get("/{material_id}/questions", response_model=List[QuestionResponse])
def get_ai_questions(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.get_ai_questions(
        db=db,
        material_id=material_id,
        current_user=current_user,
    )


@router.get(
    "/{material_id}/download",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Material file download",
        }
    },
)
def download_material(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
):
    path, filename = MaterialService.get_material_download(
        db,
        material_id,
        current_user,
    )
    return FileResponse(path=path, filename=filename)

@router.get("/{material_id}", response_model=MaterialDetailResponse)
def get_material_detail(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.get_material_detail(
        db=db,
        material_id=material_id,
        current_user=current_user,
    )

@router.delete("/{material_id}")
def delete_material(
    material_id: UUID,
    cascade: bool = False,
    keep_assets: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    result = MaterialService.delete_material(
        db=db,
        material_id=material_id,
        current_user=current_user,
        cascade=cascade,
        keep_assets=keep_assets
    )
    if result.get("require_cascade"):
        raise AppException(
            status_code=409,
            error_code="MATERIAL_DELETE_REQUIRES_CASCADE",
            details={
                "require_cascade": True,
                "linked_counts": result.get("linked_counts", {}),
            },
        )
    return result

@router.post("/{material_id}/generate-questions")
def generate_questions(
    material_id: UUID,
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.generate_questions(
        db=db,
        material_id=material_id,
        request=request,
        current_user=current_user,
    )

@router.post("/{material_id}/save-questions")
def save_questions(
    material_id: UUID,
    request: SaveQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.save_questions(
        db=db,
        material_id=material_id,
        request=request,
        current_user=current_user,
    )

@router.post("/{material_id}/generate-flashcards")
def generate_flashcards(
    material_id: UUID,
    request: GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.generate_flashcards(
        db=db,
        material_id=material_id,
        request=request,
        current_user=current_user,
    )

@router.post("/{material_id}/save-flashcards")
def save_flashcards_endpoint(
    material_id: UUID,
    request: SaveFlashcardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.save_flashcards(
        db=db,
        material_id=material_id,
        request=request,
        current_user=current_user,
    )

@router.post("/{material_id}/generate-topic-brief")
def generate_topic_brief(
    material_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.generate_topic_brief(
        db=db,
        material_id=material_id,
        current_user=current_user,
    )

@router.post("/{material_id}/save-topic-brief")
def save_topic_brief_endpoint(
    material_id: UUID,
    request: SaveTopicBriefRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return MaterialService.save_topic_brief(
        db=db,
        material_id=material_id,
        request=request,
        current_user=current_user,
    )
