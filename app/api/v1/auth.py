from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.request.auth_req import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.response.auth_resp import LoginResponse, MessageResponse, TokenResponse
from app.services.auth_service import AuthService
from app.Dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new customer account
    """
    auth_service = AuthService(db)
    return auth_service.register(request)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login to account
    """
    auth_service = AuthService(db)
    return auth_service.login(request)


@router.post("/logout", response_model=MessageResponse)
async def logout(
):
    """
    Logout from account
    """
    return {"message": "Logged out successfully"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token
    """
    auth_service = AuthService(db)
    return auth_service.refresh_token(token)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for current user
    """
    auth_service = AuthService(db)
    return auth_service.change_password(current_user.id, request)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset
    """
    auth_service = AuthService(db)
    return auth_service.forgot_password(request)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using token
    """
    auth_service = AuthService(db)
    return auth_service.reset_password(request)