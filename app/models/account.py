from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enum import AccountStatusEnum, RoleEnum


class Account(BaseModel):
    __tablename__ = "accounts"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    status = Column(SQLEnum(AccountStatusEnum), default=AccountStatusEnum.ACTIVE, nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.CUSTOMER, nullable=False)

    # Relationship
    user = relationship("User", back_populates="account", uselist=False)