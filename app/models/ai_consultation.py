from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import uuid


class AIConsultation(BaseModel):
    """AI Consultation model"""
    __tablename__ = "ai_consultations"

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    skin_type = Column(String(50), nullable=True)
    skin_condition = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    budget_range = Column(String(50), nullable=True)
    other_preferences = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    recommended_products = Column(JSON, nullable=True)  # ✅ Dùng JSON thường
    session_id = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="ai_consultations")