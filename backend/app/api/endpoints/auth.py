from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate, PasswordUpdate, ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.token import LogoutResponse, RefreshTokenRequest, Token
from app.services.auth_service import AuthService
from app.services.auth_session_service import AuthSessionService
from app.services.user_service import UserService
from app.core.rate_limit import limiter

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)) -> User:
    return current_user

@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return UserService.update_profile(db, current_user, user_update)

@router.put("/me/password")
def update_password(
    password_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return UserService.update_password(db, current_user, password_data)

@router.post("/me/avatar", response_model=UserResponse)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return UserService.upload_avatar(db, current_user, file)

@router.post("/register", response_model=UserResponse)
@limiter.limit("10/minute")
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    return AuthService.register(db, user_in)

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False),
):
    return AuthService.login(db, form_data, remember_me=remember_me)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
def refresh(
    request: Request,
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    return AuthSessionService.refresh(db, payload.refresh_token)


@router.post("/logout", response_model=LogoutResponse)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    AuthSessionService.logout_current(db, payload.refresh_token)
    return {"message": "Logged out successfully."}


@router.post("/logout-all", response_model=LogoutResponse)
def logout_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    AuthSessionService.logout_all(db, current_user)
    return {"message": "All sessions logged out successfully."}

@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.forgot_password(db, req)

@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, req: ResetPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.reset_password(db, req)
