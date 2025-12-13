from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class CartItemProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    image_url: Optional[str] = None
    # THÊM 2 FIELDS NÀY:
    stock: Optional[int] = 0
    is_available: Optional[bool] = True

    class Config:
        from_attributes = True


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: CartItemProductResponse
    subtotal: Decimal
    color_id: Optional[int] = None
    size_id: Optional[int] = None

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    customer_id: int
    cart_items: List[CartItemResponse]
    total_items: int
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True