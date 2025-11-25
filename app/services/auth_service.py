from sqlalchemy.orm import Session
from app.models import User, Account, Customer
from app.core.security import SecurityUtils, JWTManager
from app.core.email import EmailService
from app.schemas.request.auth_req import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.exceptions import (
    InvalidCredentialsException, ConflictException,
    NotFoundException, BadRequestException, InvalidTokenException
)
from app.enum import RoleEnum, AccountStatusEnum


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, request: RegisterRequest):
        """Register new customer"""

        # Check if username exists
        existing_account = self.db.query(Account).filter_by(
            username=request.username
        ).first()
        if existing_account:
            raise ConflictException("Username already exists")

        # Check if email exists
        existing_user = self.db.query(User).filter_by(
            email=request.email
        ).first()
        if existing_user:
            raise ConflictException("Email already exists")

        # Create user
        user = User(
            full_name=request.full_name,
            email=request.email,
            phone=request.phone,
            dob=request.dob,
            gender=request.gender
        )
        self.db.add(user)
        self.db.flush()

        # Create account - CODE NÀY ĐÃ ĐÚNG
        hashed_password = SecurityUtils.get_password_hash(request.password)
        account = Account(
            user_id=user.id,  # ĐÚNG - khớp với model
            username=request.username,
            password=hashed_password,
            role=RoleEnum.CUSTOMER,
            status=AccountStatusEnum.ACTIVE
        )
        self.db.add(account)
        self.db.flush()

        # Create customer
        customer = Customer(id=user.id)
        self.db.add(customer)

        self.db.commit()

        # Generate tokens
        token_data = {"user_id": user.id, "username": account.username, "role": account.role.value}
        access_token = JWTManager.create_access_token(token_data)
        refresh_token = JWTManager.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": account.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": account.role
        }

    def login(self, request: LoginRequest):
        """Login to account"""
        account = self.db.query(Account).filter_by(
            username= request.username
        ).first()

        if not account or not SecurityUtils.verify_password(request.password, account.password):
            raise InvalidCredentialsException()

        if account.status == AccountStatusEnum.LOCKED:
            raise BadRequestException("Account is locked")

        user = self.db.query(User).filter_by(id= account.user_id).first()

        # Generate tokens
        token_data = {"user_id": user.id, "username": account.username, "role": account.role.value}
        access_token = JWTManager.create_access_token(token_data)
        refresh_token = JWTManager.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": account.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": account.role
        }

    def refresh_token(self, refresh_token: str):
        """Refresh access token"""
        payload = JWTManager.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise InvalidTokenException("Invalid refresh token")

        user_id = payload.get("user_id")
        account = self.db.query(Account).filter_by(user_id= user_id).first()

        if not account:
            raise NotFoundException("User not found")

        token_data = {"user_id": user_id, "username": account.username, "role": account.role.value}
        new_access_token = JWTManager.create_access_token(token_data)
        new_refresh_token = JWTManager.create_refresh_token(token_data)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    def change_password(self, user_id: int, request: ChangePasswordRequest):
        """Change password"""
        account = self.db.query(Account).filter_by(user_id= user_id).first()

        if not account:
            raise NotFoundException("Account not found")

        if not SecurityUtils.verify_password(request.old_password, account.password):
            raise BadRequestException("Old password is incorrect")

        account.password = SecurityUtils.get_password_hash(request.new_password)
        self.db.commit()

        return {"message": "Password changed successfully"}

    def forgot_password(self, request: ForgotPasswordRequest):
        """Request password reset"""
        user = self.db.query(User).filter(email= request.email).first()

        if not user:
            # Don't reveal if email exists
            return {"message": "If email exists, reset link has been sent"}

        token = JWTManager.create_reset_password_token(user.id)

        # Send reset email
        account = self.db.query(Account).filter_by(user_id= user.id).first()
        EmailService.send_reset_password_email(user.email, account.username, token)

        return {"message": "Password reset link has been sent to your email"}

    def reset_password(self, request: ResetPasswordRequest):
        """Reset password using token"""
        payload = JWTManager.decode_token(request.token)

        if not payload or payload.get("type") != "reset_password":
            raise InvalidTokenException("Invalid or expired token")

        user_id = payload.get("user_id")
        account = self.db.query(Account).filter_by(user_id= user_id).first()

        if not account:
            raise NotFoundException("Account not found")

        account.password = SecurityUtils.get_password_hash(request.new_password)
        self.db.commit()

        return {"message": "Password has been reset successfully"}