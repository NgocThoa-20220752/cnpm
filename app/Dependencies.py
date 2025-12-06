from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import JWTManager
from app.exceptions import UnauthorizedException, ForbiddenException, AccountLockedException
from app.models.account import Account
from app.models.user import User
from app.enum import RoleEnum, AccountStatusEnum
from typing import Any
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.cart_service import CartService
from app.services.order_service import OrderService

security = HTTPBearer()


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> Any:
    """
    Dependency to get current authenticated user
    """
    # HTTPBearer đã xử lý scheme "Bearer" rồi, chỉ cần lấy token
    token = credentials.credentials

    if not token:
        print("❌ DEPENDENCY DEBUG: Missing token")
        raise UnauthorizedException("Missing authorization header")

    print(f"✅ DEPENDENCY DEBUG: Token received: {token[:50]}...")

    payload = JWTManager.decode_token(token)
    if not payload:
        print("❌ DEPENDENCY DEBUG: Invalid or expired token")
        raise UnauthorizedException("Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        print("❌ DEPENDENCY DEBUG: Invalid token payload - no user_id")
        raise UnauthorizedException("Invalid token payload")

    try:
        user_id_int = int(user_id)
    except ValueError:
        print("❌ DEPENDENCY DEBUG: Invalid user_id format")
        raise UnauthorizedException("Invalid user_id format")

    print(f"✅ DEPENDENCY DEBUG: Looking for user_id: {user_id_int}")

    # Tìm account trước
    account = db.query(Account).filter_by(user_id=user_id_int).first()
    if not account:
        print(f"❌ DEPENDENCY DEBUG: Account not found for user_id: {user_id_int}")
        raise UnauthorizedException("User not found")

    # THÊM DEBUG ACCOUNT STATUS
    print(f"🔍 DEPENDENCY DEBUG: Account status: {account.status}")

    if account.status == AccountStatusEnum.LOCKED:
        print(f"❌ DEPENDENCY DEBUG: Account locked for user_id: {user_id_int}")
        raise AccountLockedException("Your account has been locked")

    # Tìm user
    user = db.query(User).filter_by(id=user_id_int).first()
    if not user:
        print(f"❌ DEPENDENCY DEBUG: User not found for user_id: {user_id_int}")
        raise UnauthorizedException("User not found")

    print(f"✅ DEPENDENCY DEBUG: Authentication successful for user_id: {user.id}")
    print(f"✅ DEPENDENCY DEBUG: User role: {account.role}")

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

def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Dependency for OrderService"""
    return OrderService(db)

def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    """Dependency for CartService"""
    return CartService(db)

def get_client_ip(request):
    return request.client.host