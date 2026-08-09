from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from app.core.correlation import canonicalize_request_id


class AuditActor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_type: Literal["user", "system"]
    user_id: UUID | None = None
    role: Literal["admin", "teacher", "student", "system"]

    @model_validator(mode="after")
    def validate_identity(self) -> "AuditActor":
        if self.actor_type == "system":
            if self.user_id is not None or self.role != "system":
                raise ValueError("System audit actors must use role=system without a user ID")
        elif self.user_id is None or self.role == "system":
            raise ValueError("User audit actors require a user ID and non-system role")
        return self


class AuditEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    id: str = Field(min_length=1, max_length=64)
    owner_id: UUID | None = None


class AuditEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=64)
    actor: AuditActor
    action: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$",
    )
    entity: AuditEntity
    outcome: Literal["success", "denied", "failure"]
    changes: dict[str, JsonValue] = Field(default_factory=dict)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, request_id: str) -> str:
        canonical = canonicalize_request_id(request_id)
        if canonical is None:
            raise ValueError("request_id must be a UUID or Crockford ULID")
        return canonical


class AuditEventRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    occurred_at: datetime
    request_id: str
    actor: AuditActor
    action: str
    entity: AuditEntity
    outcome: Literal["success", "denied", "failure"]
    changes: dict[str, JsonValue]
    metadata: dict[str, JsonValue]

    @classmethod
    def from_record(cls, record: object) -> "AuditEventRead":
        return cls(
            event_id=getattr(record, "event_id"),
            occurred_at=getattr(record, "occurred_at"),
            request_id=getattr(record, "request_id"),
            actor=AuditActor(
                actor_type=getattr(record, "actor_type"),
                user_id=getattr(record, "actor_id"),
                role=getattr(record, "actor_role"),
            ),
            action=getattr(record, "action"),
            entity=AuditEntity(
                type=getattr(record, "entity_type"),
                id=getattr(record, "entity_id"),
                owner_id=getattr(record, "owner_id"),
            ),
            outcome=getattr(record, "outcome"),
            changes=getattr(record, "changes"),
            metadata=getattr(record, "event_metadata"),
        )
