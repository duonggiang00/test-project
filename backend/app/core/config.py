from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Exam MVP"
    ENV: str = "development"

    # DATABASE_URL is canonical. Component fields remain supported during the
    # transition from the original project configuration.
    DATABASE_URL: str | None = None
    TEST_DATABASE_URL: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_SERVER: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_DB: str | None = None

    SECRET_KEY: str
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    OPENROUTER_API_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_REMEMBER_DAYS: int = 30
    REFRESH_TOKEN_RACE_SECONDS: int = 5

    # AI provider/model policy (AI-001). `AI_DEFAULT_MODEL` is the fallback
    # for every use case; each `AI_MODEL_*` field overrides a single use
    # case without touching the others. All default to the model that was
    # previously hardcoded, so unset values do not change behavior.
    AI_PROVIDER: str = "openrouter"
    AI_DEFAULT_MODEL: str = "meta-llama/llama-3.1-8b-instruct"
    AI_MODEL_CHAT: str = ""
    AI_MODEL_QUESTION_GENERATION: str = ""
    AI_MODEL_FLASHCARD_GENERATION: str = ""
    AI_MODEL_TOPIC_BRIEF_GENERATION: str = ""
    # Material chat/retrieval is part of the active MVP surface. Operators can
    # still set this server-side flag to false as an emergency kill switch.
    RAG_ENABLED: bool = True
    # Compatibility-only mock processing endpoint. Real uploads already use
    # the governed extraction/chunking pipeline, so this remains opt-in.
    RAG_LEGACY_PROCESS_ENABLED: bool = False

    # Per-model token pricing for the §2.4 `estimated_cost` audit field
    # (AI-003), as a JSON object:
    #   {"<model-id>": {"input_per_1k_usd": "0.0002",
    #                   "output_per_1k_usd": "0.0006"}}
    # Deliberately empty by default. There is no approved price list in this
    # project, and a hardcoded default rate would put a fabricated number in
    # an audit record. With no entry for the calling model, AI audit events
    # record the real token counts and `"estimated_cost": null` -- see
    # `app/ai/cost_policy.py`.
    AI_TOKEN_PRICING: str = ""

    @model_validator(mode="after")
    def validate_database_configuration(self) -> Self:
        if self.DATABASE_URL:
            return self

        component_names = (
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_SERVER",
            "POSTGRES_PORT",
            "POSTGRES_DB",
        )
        missing = [name for name in component_names if getattr(self, name) in (None, "")]
        if missing:
            raise ValueError(
                "DATABASE_URL or all PostgreSQL component settings are required; "
                f"missing: {', '.join(missing)}"
            )
        return self

    @property
    def BASE_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.rstrip("/")

        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def ISOLATED_TEST_DATABASE_URL(self) -> str:
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL.rstrip("/")

        base_url = make_url(self.BASE_DATABASE_URL)
        if not base_url.database:
            raise ValueError("DATABASE_URL must include a database name")
        return base_url.set(database=f"{base_url.database}_test").render_as_string(
            hide_password=False
        )

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        if self.ENV.casefold() == "test":
            return self.ISOLATED_TEST_DATABASE_URL
        return self.BASE_DATABASE_URL

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Pydantic BaseSettings supplies required values from the validated environment.
settings = Settings()  # type: ignore[call-arg]
