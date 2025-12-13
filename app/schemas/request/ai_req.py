from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

class AIChatRequest(BaseModel):
    """Request cho AI chat tư vấn mỹ phẩm"""
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None)
    user_id: Optional[int] = Field(None)
    skin_type: Optional[str] = Field(None)
    budget: Optional[Decimal] = Field(None)


class TestAIRequest(BaseModel):
    """Request test AI connection"""
    test_message: Optional[str] = Field(default="Tôi có da dầu")