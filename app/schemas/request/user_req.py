from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date
from app.enum import GenderEnum, AccountStatusEnum

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)
    dob: Optional[date] = None
    gender: Optional[GenderEnum] = None
    avatar: Optional[str] = None

class UpdateAccountStatusRequest(BaseModel):
    status: AccountStatusEnum

class CreateEmployeeRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)
    dob: Optional[date] = None
    gender: Optional[GenderEnum] = None
    employee_code: str = Field(..., max_length=20)
    hire_date: date
    work_schedule: Optional[dict] = None

class UpdateEmployeeRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)
    dob: Optional[date] = None
    gender: Optional[GenderEnum] = None
    employee_code: Optional[str] = Field(None, max_length=20)
    hire_date: Optional[date] = None
    work_schedule: Optional[dict] = None
