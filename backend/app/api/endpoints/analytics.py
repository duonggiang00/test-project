from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    ScoreStatsResponse,
    CompletionStatusResponse,
    TopicPerformanceResponse
)
from app.api.deps import get_current_active_teacher
from app.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return AnalyticsService.get_overview(db)

@router.get("/score-stats", response_model=ScoreStatsResponse)
def get_score_stats(
    exam_id: Optional[UUID] = None,
    topic_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return AnalyticsService.get_score_stats(db, exam_id, topic_id)

@router.get("/completion-status", response_model=CompletionStatusResponse)
def get_completion_status(
    exam_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return AnalyticsService.get_completion_status(db, exam_id)

@router.get("/topic-performance", response_model=List[TopicPerformanceResponse])
def get_topic_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher)
):
    return AnalyticsService.get_topic_performance(db)
