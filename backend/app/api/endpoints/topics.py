from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.db.session import get_db
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.services.topic_service import TopicService
from app.api.deps import get_current_active_teacher, get_current_user
from app.models.user import User
from app.core.exceptions import AppException

router = APIRouter()

@router.get("", response_model=Page[TopicResponse])
def get_topics(search: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all topics with pagination and optional search by name.
    """
    query = TopicService.get_topics_query(db, search)
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
def get_topic(topic_id: UUID, db: Session = Depends(get_db)):
    return TopicService.get_topic(db, topic_id)

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

@router.get("/{topic_id}/progress")
def get_topic_progress(
    topic_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's progress percentage for a topic.
    """
    progress = TopicService.get_topic_progress(db, topic_id, current_user.id)
    return {"progress": progress}
