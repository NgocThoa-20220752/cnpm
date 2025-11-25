from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.schemas.request.user_req import (
    UpdateUserRequest, UpdateAccountStatusRequest,
    CreateEmployeeRequest, UpdateEmployeeRequest
)
from app.schemas.response.user_resp import (
    UserResponse, AccountResponse, EmployeeResponse,
    UserListResponse
)
from app.schemas.response.auth_resp import MessageResponse
from app.services.user_service import UserService
from app.Dependencies import (
    get_current_user, get_current_admin,
    get_admin_or_employee
)
from app.models.user import User
from app.functions.file_utils import FileUtils

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    print(f"🔍 ENDPOINT DEBUG: Current user ID: {current_user.id}")
    print(f"🔍 ENDPOINT DEBUG: Current user role: {current_user.account_info.role}")
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
        request: UpdateUserRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Update current user information"""
    user_service = UserService(db)
    return user_service.update_user(current_user.id, request)


@router.post("/me/avatar", response_model=MessageResponse)
async def upload_avatar(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Upload user avatar"""
    file_path = await FileUtils.save_upload_file(file, "avatars")

    user_service = UserService(db)
    update_request = UpdateUserRequest(avatar=file_path)
    user_service.update_user(current_user.id, update_request)

    return {"message": "Avatar uploaded successfully"}


@router.delete("/me", response_model=MessageResponse)
async def delete_current_user(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Delete current user account"""
    user_service = UserService(db)
    return user_service.delete_user(current_user.id)


# Admin/Employee routes
@router.get("", response_model=UserListResponse)
async def get_all_users(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_admin_or_employee)
):
    """Get all users (Admin/Employee only)"""
    user_service = UserService(db)
    return user_service.get_all_accounts(page, limit, search)


@router.get("/{user_id}", response_model=AccountResponse)
async def get_user_by_id(
        user_id: int,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_admin_or_employee)
):
    """Get user by ID (Admin/Employee only)"""
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    return user.account


@router.put("/{user_id}/status", response_model=MessageResponse)
async def update_user_status(
        user_id: int,
        request: UpdateAccountStatusRequest,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_admin_or_employee)
):
    """Update user account status (Admin/Employee only)"""
    user_service = UserService(db)
    return user_service.update_account_status(user_id, request)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_admin_or_employee)
):
    """Delete user (Admin/Employee only)"""
    user_service = UserService(db)
    user_service.delete_user(user_id)
    return None


# Employee management (Admin only)
@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
        request: CreateEmployeeRequest,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_current_admin)
):
    """Create employee account (Admin only)"""
    user_service = UserService(db)
    return user_service.create_employee(request)


@router.get("/employees/list/all")
async def get_all_employees(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_current_admin)
):
    """Get all employees (Admin only)"""
    user_service = UserService(db)
    return user_service.get_all_employees(page, limit)


@router.put("/employees/{user_id}", response_model=EmployeeResponse)
async def update_employee(
        user_id: int,
        request: UpdateEmployeeRequest,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_current_admin)
):
    """Update employee (Admin only)"""
    user_service = UserService(db)
    return user_service.update_employee(user_id, request)


@router.delete("/employees/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
        user_id: int,
        db: Session = Depends(get_db),
        _current_user: User = Depends(get_current_admin)
):
    """Delete employee (Admin only)"""
    user_service = UserService(db)
    user_service.delete_employee(user_id)
    return None