"""Per-use-case provider/model resolution (AI-001).

Replaces the hardcoded model string that used to live directly in
`ai_studio_service.py` and `material_service.py`. The default resolved
model is unchanged from before this module existed -- only its source
(validated settings, per use case) is new.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.core.config import Settings, settings as default_settings


class ModelUseCase(str, Enum):
    CHAT = "chat"
    QUESTION_GENERATION = "question_generation"
    FLASHCARD_GENERATION = "flashcard_generation"
    TOPIC_BRIEF_GENERATION = "topic_brief_generation"


class UnknownModelUseCaseError(ValueError):
    """Raised when a use case cannot be resolved to a known policy entry."""

    def __init__(self, use_case: object) -> None:
        super().__init__(f"Unknown AI model use case: {use_case!r}")
        self.use_case = use_case


@dataclass(frozen=True)
class ModelPolicyEntry:
    provider: str
    model: str


# Maps each use case to the settings field that overrides its model. Every
# use case falls back to `AI_DEFAULT_MODEL` when its override is unset.
_USE_CASE_SETTINGS_FIELD: dict[ModelUseCase, str] = {
    ModelUseCase.CHAT: "AI_MODEL_CHAT",
    ModelUseCase.QUESTION_GENERATION: "AI_MODEL_QUESTION_GENERATION",
    ModelUseCase.FLASHCARD_GENERATION: "AI_MODEL_FLASHCARD_GENERATION",
    ModelUseCase.TOPIC_BRIEF_GENERATION: "AI_MODEL_TOPIC_BRIEF_GENERATION",
}


def resolve_model_config(
    use_case: ModelUseCase | str,
    *,
    settings_obj: Settings | None = None,
) -> ModelPolicyEntry:
    """Resolve the provider/model to use for `use_case`.

    Accepts either a `ModelUseCase` member or its string value so callers
    that only have a raw string (e.g. from configuration) get a clear,
    typed failure instead of a `KeyError`/`AttributeError`.
    """
    resolved_settings = settings_obj if settings_obj is not None else default_settings

    if isinstance(use_case, ModelUseCase):
        resolved_use_case = use_case
    else:
        try:
            resolved_use_case = ModelUseCase(use_case)
        except ValueError as exc:
            raise UnknownModelUseCaseError(use_case) from exc

    field_name = _USE_CASE_SETTINGS_FIELD[resolved_use_case]
    override = getattr(resolved_settings, field_name, "") or ""
    model = override or resolved_settings.AI_DEFAULT_MODEL
    return ModelPolicyEntry(provider=resolved_settings.AI_PROVIDER, model=model)
