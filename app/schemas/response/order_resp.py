from pydantic import BaseModel
from typing import List, Optional, Any
from decimal import Decimal
from datetime import datetime
from app.enum import PaymentMethodEnum, PaymentStatusEnum, OrderStatusEnum


class OrderItemProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product: OrderItemProductResponse

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_code: str
    customer_id: int
    total_amount: Decimal
    payment_method: PaymentMethodEnum
    payment_status: PaymentStatusEnum
    order_status: OrderStatusEnum
    shipping_address: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    id: int
    order_code: str
    customer_id: int
    customer_name: str
    customer_phone: str
    total_amount: Decimal
    payment_method: PaymentMethodEnum
    payment_status: PaymentStatusEnum
    order_status: OrderStatusEnum
    shipping_address: str
    order_items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[OrderResponse]

class OrderWithPaymentResponse(BaseModel):
    order: OrderResponse
    payment_result: Optional[Any] = None

    class Config:
        from_attributes = True