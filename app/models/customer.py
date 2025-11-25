from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    user = relationship("User", back_populates="customer", uselist=False)
    carts = relationship("Cart", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    ai_consultations = relationship("AIConsultation", back_populates="customer", cascade="all, delete-orphan")