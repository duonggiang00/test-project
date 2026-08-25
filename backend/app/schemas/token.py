from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.schemas.user import UserResponse

class Token(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    token_type: str
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutResponse(BaseModel):
    message: str

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    session_family_id: Optional[UUID] = None
    token_type: Optional[str] = None
