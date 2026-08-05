from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List, Optional

class AnalyticsOverviewResponse(BaseModel):
    total_students: int
    total_exams: int
    total_questions: int
    total_submissions: int
    overall_avg_score: float
    completion_rate: float
    total_topics: Optional[int] = 0
    pass_rate: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)

class ScoreDistributionBucket(BaseModel):
    range_label: str
    count: int

    model_config = ConfigDict(from_attributes=True)

class ScoreStatsResponse(BaseModel):
    highest_score: float
    lowest_score: float
    average_score: float
    median_score: float
    distribution: List[ScoreDistributionBucket]

    model_config = ConfigDict(from_attributes=True)

class CompletionStatusResponse(BaseModel):
    completed: int
    in_progress: int
    completed_count: Optional[int] = 0
    in_progress_count: Optional[int] = 0
    not_started_count: Optional[int] = 0
    total_assigned: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

class TopicPerformanceResponse(BaseModel):
    topic_id: UUID
    topic_name: str
    avg_score_percentage: float
    total_attempts: int

    model_config = ConfigDict(from_attributes=True)
