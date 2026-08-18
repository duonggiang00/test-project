import pytest

from app.core.config import Settings
from app.ai.model_policy import (
    ModelUseCase,
    UnknownModelUseCaseError,
    resolve_model_config,
)


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "DATABASE_URL": "postgresql://app:password@database:5432/app",
        "SECRET_KEY": "test-only-secret",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.unit
@pytest.mark.parametrize(
    "use_case",
    [
        ModelUseCase.CHAT,
        ModelUseCase.QUESTION_GENERATION,
        ModelUseCase.FLASHCARD_GENERATION,
        ModelUseCase.TOPIC_BRIEF_GENERATION,
    ],
)
def test_every_use_case_defaults_to_the_configured_default_model(use_case):
    settings_obj = _settings()

    resolved = resolve_model_config(use_case, settings_obj=settings_obj)

    assert resolved.provider == "openrouter"
    assert resolved.model == "meta-llama/llama-3.1-8b-instruct"


def test_default_model_matches_the_historical_hardcoded_model():
    # AI-001 replaces the hardcoded model string with configuration, but the
    # resolved default must stay identical so behavior does not change.
    settings_obj = _settings()

    for use_case in ModelUseCase:
        assert (
            resolve_model_config(use_case, settings_obj=settings_obj).model
            == "meta-llama/llama-3.1-8b-instruct"
        )


def test_per_use_case_override_only_affects_that_use_case():
    settings_obj = _settings(AI_MODEL_QUESTION_GENERATION="anthropic/claude-3-haiku")

    assert (
        resolve_model_config(
            ModelUseCase.QUESTION_GENERATION, settings_obj=settings_obj
        ).model
        == "anthropic/claude-3-haiku"
    )
    assert (
        resolve_model_config(ModelUseCase.CHAT, settings_obj=settings_obj).model
        == "meta-llama/llama-3.1-8b-instruct"
    )


def test_provider_override_is_read_from_settings():
    settings_obj = _settings(AI_PROVIDER="custom-provider")

    resolved = resolve_model_config(ModelUseCase.CHAT, settings_obj=settings_obj)

    assert resolved.provider == "custom-provider"


def test_string_use_case_value_resolves_the_same_as_the_enum_member():
    settings_obj = _settings()

    assert resolve_model_config(
        "question_generation", settings_obj=settings_obj
    ) == resolve_model_config(ModelUseCase.QUESTION_GENERATION, settings_obj=settings_obj)


def test_unknown_use_case_fails_clearly():
    settings_obj = _settings()

    with pytest.raises(UnknownModelUseCaseError, match="essay_grading"):
        resolve_model_config("essay_grading", settings_obj=settings_obj)
