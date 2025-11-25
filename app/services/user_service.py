from sqlalchemy.orm import Session
from typing import Optional

from app.models import Customer
from app.models.user import User
from app.models.account import Account
from app.models.employee import Employee
from app.core.security import SecurityUtils
from app.schemas.request.user_req import (
    UpdateUserRequest, UpdateAccountStatusRequest,
    CreateEmployeeRequest, UpdateEmployeeRequest
)
from app.exceptions import NotFoundException, ConflictException
from app.enum import AccountStatusEnum, RoleEnum


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        user = self.db.query(User).filter_by(id= user_id).first()
        if not user:
            raise NotFoundException("User not found")
        return user

    def update_user(self, user_id: int, request: UpdateUserRequest):
        user = self.get_user_by_id(user_id)

        if request.full_name is not None:
            user.full_name = request.full_name
        if request.phone is not None:
            user.phone = request.phone
        if request.dob is not None:
            user.dob = request.dob
        if request.gender is not None:
            user.gender = request.gender
        if request.avatar is not None:
            user.avatar = request.avatar

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int):
        try:
            # Tìm user và các related records
            user = self.db.query(User).filter_by(id= user_id).first()
            if not user:
                raise NotFoundException("User not found")

            # Tìm và xóa account
            account = self.db.query(Account).filter_by(user_id= user_id).first()
            if account:
                self.db.delete(account)

            # Tìm và xóa customer record (nếu có)
            customer = self.db.query(Customer).filter_by(id= user_id).first()
            if customer:
                self.db.delete(customer)

            # Xóa user
            self.db.delete(user)

            self.db.commit()
            return {"message": "User deleted successfully"}

        except Exception as e:
            self.db.rollback()
            print(f"❌ Delete user error: {str(e)}")
            raise
    def get_all_accounts(self, page: int = 1, limit: int = 20, search: Optional[str] = None):
        query = self.db.query(Account).join(User)

        if search:
            query = query.filter(
                (User.full_name.ilike(f"%{search}%")) |
                (User.email.ilike(f"%{search}%")) |
                (Account.username.ilike(f"%{search}%"))
            )

        total = query.count()
        accounts = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": accounts
        }

    def update_account_status(self, user_id: int, request: UpdateAccountStatusRequest):
        account = self.db.query(Account).filter_by(user_id= user_id).first()
        if not account:
            raise NotFoundException("Account not found")

        account.status = AccountStatusEnum(request.status)
        self.db.commit()
        self.db.refresh(account)
        return {"message": "Account status updated successfully"}

    def create_employee(self, request: CreateEmployeeRequest):
        # Check if username exists
        existing_account = self.db.query(Account).filter_by(
            username= request.username
        ).first()
        if existing_account:
            raise ConflictException("Username already exists")

        # Check if email exists
        existing_user = self.db.query(User).filter_by(
            email= request.email
        ).first()
        if existing_user:
            raise ConflictException("Email already exists")

        # Check if employee_code exists
        existing_employee = self.db.query(Employee).filter_by(
            employee_code= request.employee_code
        ).first()
        if existing_employee:
            raise ConflictException("Employee code already exists")

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

        # Create account
        hashed_password = SecurityUtils.get_password_hash(request.password)
        account = Account(
            user_id=user.id,
            username=request.username,
            password=hashed_password,
            role=RoleEnum.EMPLOYEE,
            status=AccountStatusEnum.ACTIVE
        )
        self.db.add(account)
        self.db.flush()

        # Create employee
        employee = Employee(
            id=user.id,
            employee_code=request.employee_code,
            hire_date=request.hire_date,
            work_schedule=request.work_schedule
        )
        self.db.add(employee)

        self.db.commit()
        self.db.refresh(employee)
        return employee

    def update_employee(self, user_id: int, request: UpdateEmployeeRequest):
        employee = self.db.query(Employee).filter_by(id= user_id).first()
        if not employee:
            raise NotFoundException("Employee not found")

        user = self.db.query(User).filter_by(id= user_id).first()

        # Update user info
        if request.full_name is not None:
            user.full_name = request.full_name
        if request.phone is not None:
            user.phone = request.phone
        if request.dob is not None:
            user.dob = request.dob
        if request.gender is not None:
            user.gender = request.gender

        # Update employee info
        if request.employee_code is not None:
            # Check if new employee_code exists
            existing = self.db.query(Employee).filter_by(
                employee_code= request.employee_code
            ).filter(
                Employee.id.ne(user_id)
            ).first()
            if existing:
                raise ConflictException("Employee code already exists")
            employee.employee_code = request.employee_code

        if request.hire_date is not None:
            employee.hire_date = request.hire_date
        if request.work_schedule is not None:
            employee.work_schedule = request.work_schedule

        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_all_employees(self, page: int = 1, limit: int = 20):
        query = self.db.query(Employee)
        total = query.count()
        employees = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": employees
        }

    def delete_employee(self, user_id: int):
        employee = self.db.query(Employee).filter_by(id= user_id).first()
        if not employee:
            raise NotFoundException("Employee not found")

        # This will cascade delete user and account
        user = self.db.query(User).filter_by(id= user_id).first()
        self.db.delete(user)
        self.db.commit()
        return {"message": "Employee deleted successfully"}