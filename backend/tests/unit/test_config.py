from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT, ROOT_ENV_FILE, Settings


def test_root_env_file_is_independent_of_working_directory():
    assert ROOT_ENV_FILE == PROJECT_ROOT / ".env"
    assert ROOT_ENV_FILE == Path(__file__).resolve().parents[3] / ".env"


def test_database_url_is_the_canonical_database_setting():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://app:password@database:5432/app",
        SECRET_KEY="test-only-secret",
    )

    assert configured.SQLALCHEMY_DATABASE_URL == (
        "postgresql://app:password@database:5432/app"
    )


def test_legacy_postgresql_components_remain_supported():
    configured = Settings(
        _env_file=None,
        POSTGRES_USER="app",
        POSTGRES_PASSWORD="password",
        POSTGRES_SERVER="database",
        POSTGRES_PORT=5432,
        POSTGRES_DB="app",
        SECRET_KEY="test-only-secret",
    )

    assert configured.SQLALCHEMY_DATABASE_URL == (
        "postgresql://app:password@database:5432/app"
    )


def test_database_configuration_is_required():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, SECRET_KEY="test-only-secret")


def test_cors_origins_are_normalized():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://app:password@database:5432/app",
        SECRET_KEY="test-only-secret",
        BACKEND_CORS_ORIGINS="http://localhost:3000/, https://example.test ",
    )

    assert configured.cors_origins == [
        "http://localhost:3000",
        "https://example.test",
    ]


def test_test_environment_derives_an_isolated_database_name():
    configured = Settings(
        _env_file=None,
        ENV="test",
        DATABASE_URL="postgresql://app:password@localhost:5432/app",
        SECRET_KEY="test-only-secret",
    )

    assert configured.BASE_DATABASE_URL.endswith("/app")
    assert configured.SQLALCHEMY_DATABASE_URL.endswith("/app_test")


def test_explicit_test_database_url_overrides_the_derived_target():
    configured = Settings(
        _env_file=None,
        ENV="test",
        DATABASE_URL="postgresql://app:password@localhost:5432/app",
        TEST_DATABASE_URL="postgresql://app:password@localhost:5432/custom_test",
        SECRET_KEY="test-only-secret",
    )

    assert configured.SQLALCHEMY_DATABASE_URL.endswith("/custom_test")


def test_rag_retrieval_and_embedding_policy_is_strict():
    configured = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://app:password@localhost:5432/app",
        SECRET_KEY="test-only-secret",
    )

    assert configured.RAG_RETRIEVAL_MODE == "hybrid"
    assert configured.AI_EMBEDDING_MODEL == "openai/text-embedding-3-small"
    assert configured.AI_EMBEDDING_DIMENSIONS == 1536

    from_environment = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://app:password@localhost:5432/app",
        SECRET_KEY="test-only-secret",
        AI_EMBEDDING_DIMENSIONS="1536",
    )
    assert from_environment.AI_EMBEDDING_DIMENSIONS == 1536

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql://app:password@localhost:5432/app",
            SECRET_KEY="test-only-secret",
            RAG_RETRIEVAL_MODE="unknown",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            DATABASE_URL="postgresql://app:password@localhost:5432/app",
            SECRET_KEY="test-only-secret",
            AI_EMBEDDING_DIMENSIONS=3072,
        )
