from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class TopicBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    brief_content: Optional[str] = None
    brief_ai_generated: Optional[bool] = False

class TopicCreate(TopicBase):
    pass

class TopicUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None

class TopicBriefUpdate(BaseModel):
    brief_content: str
    brief_ai_generated: bool = False

class TopicResponse(TopicBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
