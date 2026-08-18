"""Request/response contracts for the AI generation review queue (AI-002).

The *draft* models here are deliberately separate from the request models
that used to feed `MaterialService.save_*`. Those request models let a
caller post arbitrary content straight into `Question`/`Flashcard`/
`TopicBrief`; these describe content that already exists inside a reviewed
`AIGenerationJob.draft_payload`, so publishing reads them from the job and
never from the request body. `PublishJobRequest` therefore carries only
*placement* fields (which topic, what to call the deck/brief) -- a reviewer
chooses where approved content lands, but cannot substitute what it says.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.material import OptionSchema


class AIGenerationJobResponse(BaseModel):
    id: UUID
    owner_id: UUID
    material_id: UUID
    use_case: str
    status: str
    version: int
    draft_payload: Optional[Any] = None
    failure_code: Optional[str] = None
    reviewer_id: Optional[UUID] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewDecisionRequest(BaseModel):
    """Optional optimistic-concurrency guard for approve/reject/publish.

    A reviewer acting from a stale list gets `AI_JOB_VERSION_CONFLICT`
    instead of silently overwriting a decision another reviewer already
    made. Omitting it falls back to the row lock plus the transition
    allowlist, which already refuse a second decision.
    """

    expected_version: Optional[int] = None


class PublishJobRequest(ReviewDecisionRequest):
    title: Optional[str] = None
    topic_id: Optional[str] = None


class QuestionDraft(BaseModel):
    """One proposed question inside `draft_payload`.

    `type`/`difficulty` carry defaults because a provider response is not
    guaranteed to supply them; `save_questions` applied the same two
    fallbacks (`MULTIPLE_CHOICE`, `MEDIUM`) after the fact, so publishing a
    draft that omits them behaves exactly as the removed direct save did.
    """

    type: str = "MULTIPLE_CHOICE"
    content: str
    points: int = 1
    difficulty: Optional[str] = "MEDIUM"
    source_reference: Optional[str] = None
    explanation: Optional[str] = None
    options: list[OptionSchema] = []
    metadata_json: Optional[dict] = None


class FlashcardDraft(BaseModel):
    term: str
    definition: str
    source_reference: Optional[str] = None
    explanation: Optional[str] = None
