from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class ProductRecommendation(BaseModel):
    """Sản phẩm được AI đề xuất"""
    id: int = Field(...)
    name: str = Field(...)
    price: Decimal = Field(...)
    category: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    image_url: Optional[str] = Field(None)
    sku: Optional[str] = Field(None)
    skin_type: List[str] = Field(...)
    benefits: List[str] = Field(...)


class AIChatResponse(BaseModel):
    """Response cho AI chat"""
    reply: str = Field(...)
    intent: str = Field(...)
    session_id: str = Field(...)
    extracted_info: Optional[Dict[str, Any]] = Field(None)
    products: List[ProductRecommendation] = Field(...)
    timestamp: datetime = Field(default_factory=datetime.now)


class TestAIResponse(BaseModel):
    """Response test AI"""
    status: str = Field(...)
    ollama_connected: bool = Field(...)
    database_connected: bool = Field(...)
    model: str = Field(...)
    architecture: str = Field(...)
    test_results: List[Dict[str, Any]] = Field(...)


class ErrorResponse(BaseModel):
    """Response khi có lỗi"""
    error: str = Field(...)
    detail: Optional[str] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    """Response health check"""
    status: str = Field(...)
    database: str = Field(...)
    ai_service: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.now)