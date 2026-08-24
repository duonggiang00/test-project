from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.services.topic_service import TopicService
from app.api.deps import (
    get_current_active_student,
    get_current_active_teacher,
    get_current_user,
)
from app.models.user import User

router = APIRouter()

@router.get("", response_model=Page[TopicResponse])
def get_topics(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all topics with pagination and optional search by name.
    """
    query = TopicService.get_topics_query(db, current_user, search)
    return paginate(db, query)

@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Create a new topic. (Requires teacher/admin authentication)
    """
    return TopicService.create_topic(db, topic_in, current_user)

@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TopicService.get_topic(db, topic_id, current_user)

@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: UUID,
    topic_in: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Update topic information. (Requires teacher/admin authentication)
    """
    return TopicService.update_topic(db, topic_id, topic_in, current_user)

@router.delete("/{topic_id}", status_code=status.HTTP_200_OK)
def delete_topic(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Delete a topic. (Requires teacher/admin authentication)
    """
    TopicService.delete_topic(db, topic_id, current_user)
    return {"message": "Topic deleted successfully", "id": str(topic_id)}

@router.post("/{topic_id}/restore", response_model=TopicResponse)
def restore_topic(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    """
    Restore a soft-deleted topic within the 30-day retention window.
    (Requires owner or admin authentication)
    """
    return TopicService.restore_topic(db, topic_id, current_user)

@router.get("/{topic_id}/progress")
def get_topic_progress(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_student)
):
    """
    Get the current user's progress percentage for a topic.
    """
    progress = TopicService.get_topic_progress(db, topic_id, current_user)
    return {"progress": progress}
