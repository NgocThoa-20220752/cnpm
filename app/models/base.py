from sqlalchemy import Column, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.core.database import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base, TimestampMixin):
    """Base model with id and timestamps"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)