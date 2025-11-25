from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.enum import GenderEnum, RoleEnum, AccountStatusEnum


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    dob: Optional[date]
    gender: Optional[GenderEnum]
    avatar: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    id: int
    username: str
    role: RoleEnum
    status: AccountStatusEnum
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True


class EmployeeResponse(BaseModel):
    id: int
    employee_code: str
    hire_date: date
    work_schedule: Optional[dict]
    user: UserResponse

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[AccountResponse]