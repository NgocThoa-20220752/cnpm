from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

import os

from app.core.database import get_db
from app.services.ai_service import AIProductAdvisorService

router = APIRouter(tags=["AI Product Advisor"])


# ==================== REQUEST/RESPONSE SCHEMAS ====================

class ChatMessage(BaseModel):
    """Message trong conversation"""
    role: str = Field(..., description="Role: 'user' hoặc 'assistant'")
    content: str = Field(..., description="Nội dung tin nhắn")


class ProductAdviceRequest(BaseModel):
    """Request tư vấn sản phẩm"""
    query: str = Field(..., min_length=1, description="Câu hỏi/yêu cầu của khách hàng")
    conversation_history: Optional[List[ChatMessage]] = Field(
        None,
        description="Lịch sử hội thoại trước đó (optional)"
    )


class ProductSummary(BaseModel):
    """Thông tin tóm tắt sản phẩm"""
    id: int
    name: str
    slug: str
    category: Optional[dict] = None
    price_range: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class ProductAdviceResponse(BaseModel):
    """Response tư vấn sản phẩm"""
    advice: str = Field(..., description="Lời tư vấn từ AI")
    products: List[ProductSummary] = Field(..., description="Danh sách sản phẩm được gợi ý")
    product_count: int = Field(..., description="Số lượng sản phẩm gợi ý")


class HealthCheckResponse(BaseModel):
    """Response kiểm tra sức khỏe hệ thống AI"""
    status: str
    ollama_url: str
    ollama_available: bool
    message: str


# ==================== ENDPOINTS ====================

@router.post("/advise", response_model=ProductAdviceResponse)
async def advise_products(
        request: ProductAdviceRequest,
        db: Session = Depends(get_db)
):
    """
    Tư vấn sản phẩm dựa trên yêu cầu của khách hàng

    **Ví dụ query:**
    - "Tôi muốn tìm kem chống nắng cho da dầu"
    - "Có son màu đỏ nào giá dưới 200k không?"
    - "Sản phẩm nào tốt cho da khô?"
    """
    try:
        # Lấy Ollama URL từ env hoặc dùng default
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        # Khởi tạo service
        ai_service = AIProductAdvisorService(db=db, ollama_url=ollama_url)

        # Chuyển đổi conversation history sang format dict
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        # Gọi AI tư vấn
        result = ai_service.advise_products(
            user_query=request.query,
            conversation_history=history
        )

        return ProductAdviceResponse(
            advice=result["advice"],
            products=result["products"],
            product_count=result["product_count"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tư vấn sản phẩm: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def check_health():
    """
    Kiểm tra sức khỏe của hệ thống AI advisor
    """
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    try:
        import requests
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        ollama_available = response.status_code == 200
        message = "Hệ thống AI hoạt động bình thường" if ollama_available else "Không thể kết nối với Ollama"
    except Exception as e:
        ollama_available = False
        message = f"Lỗi kết nối Ollama: {str(e)}"

    return HealthCheckResponse(
        status="healthy" if ollama_available else "unhealthy",
        ollama_url=ollama_url,
        ollama_available=ollama_available,
        message=message
    )


@router.get("/product-context")
async def get_product_context(db: Session = Depends(get_db)):
    """
    Lấy toàn bộ context sản phẩm (dùng để debug/kiểm tra)
    """
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        ai_service = AIProductAdvisorService(db=db, ollama_url=ollama_url)
        context = ai_service.get_product_context()

        return {
            "context": context,
            "length": len(context)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy context: {str(e)}"
        )