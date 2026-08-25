from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.core.security_guardrails import MAX_CONTENT_LENGTH, MAX_MESSAGES


class ChatMessage(BaseModel):
    """One client-controlled chat turn accepted by the material-chat API."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)

    model_config = ConfigDict(extra="forbid")


class ChatRequest(BaseModel):
    material_id: uuid.UUID
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES * 2)

    model_config = ConfigDict(extra="forbid")


class ProcessDocumentRequest(BaseModel):
    material_id: uuid.UUID

    model_config = ConfigDict(extra="forbid")

class ProcessDocumentResponse(BaseModel):
    message: str
    chunks_created: int

    model_config = ConfigDict(from_attributes=True)
