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
import re
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

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

    @model_validator(mode="after")
    def validate_fill_in_blank_contract(self) -> "QuestionDraft":
        if self.type.upper() != "FILL_IN_BLANK":
            return self

        blanks = (self.metadata_json or {}).get("blanks")
        token_count = len(re.findall(r"\[BLANK\]", self.content))
        has_legacy_token = re.search(r"_{3,}", self.content) is not None
        if (
            not isinstance(blanks, list)
            or token_count == 0
            or token_count != len(blanks)
            or has_legacy_token
        ):
            raise ValueError(
                "Fill-in-blank content must contain one [BLANK] token per blank"
            )

        expected_indexes = list(range(token_count))
        actual_indexes: list[int] = []
        for blank in blanks:
            if not isinstance(blank, dict):
                raise ValueError("Fill-in-blank metadata must contain blank objects")
            blank_index = blank.get("blank_index")
            acceptable_answers = blank.get("acceptable_answers")
            if not isinstance(blank_index, int):
                raise ValueError("Fill-in-blank indexes must be integers")
            if (
                not isinstance(acceptable_answers, list)
                or not acceptable_answers
                or not all(
                    isinstance(answer, str) and answer.strip()
                    for answer in acceptable_answers
                )
            ):
                raise ValueError(
                    "Each fill-in-blank item requires an acceptable answer"
                )
            actual_indexes.append(blank_index)

        if sorted(actual_indexes) != expected_indexes:
            raise ValueError("Fill-in-blank indexes must be contiguous from zero")
        return self


class FlashcardDraft(BaseModel):
    term: str
    definition: str
    source_reference: Optional[str] = None
    explanation: Optional[str] = None


class TopicBriefDraft(BaseModel):
    content: str
    title: Optional[str] = None


class UpdateDraftRequest(ReviewDecisionRequest):
    """A reviewer's edit to one job's `draft_payload` before it is decided.

    Distinct from `PublishJobRequest`: this *is* allowed to carry content,
    because it only ever applies while the job is still `awaiting_review`
    (`MaterialService.update_generation_job_draft` refuses any other status).
    Publishing still reads exclusively from the job's `draft_payload` and
    still accepts no content of its own -- a reviewer can reshape a draft
    before deciding on it, but can never substitute what an *approved* draft
    says. Exactly one of the three fields is accepted, matching the job's
    `use_case`; the service rejects any other combination.
    """

    questions: Optional[list[QuestionDraft]] = None
    flashcards: Optional[list[FlashcardDraft]] = None
    content: Optional[str] = None
    title: Optional[str] = None
