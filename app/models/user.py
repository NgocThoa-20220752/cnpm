from sqlalchemy import Column, String, Date, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enum import GenderEnum


class User(BaseModel):
    __tablename__ = "users"

    full_name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=True)
    gender = Column(SQLEnum(GenderEnum), nullable=True)
    phone = Column(String(15), nullable=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    avatar = Column(Text, nullable=True)

    # relationship
    account = relationship("Account", back_populates="user", uselist=False)
    customer = relationship("Customer", back_populates="user", uselist=False)
    employee = relationship("Employee", back_populates="user", uselist=False)