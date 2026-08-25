# Import all models here for SQLAlchemy to discover them
from app.models.user import User
from app.models.material import StudyMaterial
from app.models.topic import Topic
from app.models.exam import Exam, Question, Option
from app.models.submission import Submission, SubmissionAnswer
from app.models.flashcard import FlashcardDeck, Flashcard, FlashcardProgress
from app.models.document_chunk import DocumentChunk
from app.models.topic_brief import TopicBrief
from app.models.audit_event import AuditEvent
from app.models.purge_job import PurgeJob
from app.models.ai_generation import AIGenerationJob, AIGradeSuggestion
from app.models.ai_restricted_payload import AIRestrictedPayload
from app.models.refresh_session import RefreshSession

__all__ = [
    "User",
    "StudyMaterial",
    "Topic",
    "Exam", "Question", "Option",
    "Submission", "SubmissionAnswer",
    "FlashcardDeck", "Flashcard", "FlashcardProgress",
    "DocumentChunk",
    "TopicBrief",
    "AuditEvent",
    "PurgeJob",
    "AIGenerationJob", "AIGradeSuggestion",
    "AIRestrictedPayload",
    "RefreshSession",
]
