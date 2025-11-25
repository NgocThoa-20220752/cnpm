from typing import Optional
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import JWTManager
from app.exceptions import UnauthorizedException, ForbiddenException, AccountLockedException
from app.models.account import Account
from app.models.user import User
from app.enum import RoleEnum, AccountStatusEnum
from typing import Any


def get_current_user(
        authorization: Optional[str] = Header(None),
        db: Session = Depends(get_db)
) -> Any:
    """
    Dependency to get current authenticated user
    """
    if not authorization:
        raise UnauthorizedException("Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedException("Invalid authentication scheme")
    except ValueError:
        raise UnauthorizedException("Invalid authorization header format")

    payload = JWTManager.decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    user_id_int = int(user_id)

    account = db.query(Account).filter_by(user_id=user_id_int).first()
    if not account:
        raise UnauthorizedException("User not found")

    if account.status == AccountStatusEnum.LOCKED:
        raise AccountLockedException("Your account has been locked")

    user = db.query(User).filter_by(id=user_id_int).first()
    if not user:
        raise UnauthorizedException("User not found")

    # Attach account info to user object for easy access
    user.account_info = account

    return user


def get_current_customer(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current customer
    """
    if current_user.account_info.role != RoleEnum.CUSTOMER:
        raise ForbiddenException("Customer access required")
    return current_user


def get_current_employee(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current employee
    """
    if current_user.account_info.role != RoleEnum.EMPLOYEE:
        raise ForbiddenException("Employee access required")
    return current_user


def get_current_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current admin
    """
    if current_user.account_info.role != RoleEnum.ADMIN:
        raise ForbiddenException("Admin access required")
    return current_user


def get_admin_or_employee(
        current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get admin or employee
    """
    if current_user.account_info.role not in [RoleEnum.ADMIN, RoleEnum.EMPLOYEE]:
        raise ForbiddenException("Admin or Employee access required")
    return current_user