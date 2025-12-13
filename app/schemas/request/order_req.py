from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional
from decimal import Decimal
from app.enum import PaymentMethodEnum, OrderStatusEnum

class OrderItemRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)


class CreateOrderRequest(BaseModel):
    items: List[OrderItemRequest]
    payment_method: PaymentMethodEnum
    shipping_address: str = Field(..., min_length=1)
    shipping_phone: str = Field(..., min_length=10, max_length=15)
    shipping_fee: Decimal = Field(0.0, ge=0)
    customer_note: str = Field(None, max_length=500)

    # THÊM 2 TRƯỜNG QUAN TRỌNG
    total_amount: Decimal = Field(..., gt=0, description="Tổng tiền sản phẩm")
    final_amount: Decimal = Field(..., gt=0, description="Tổng thanh toán (đã + ship)")

    @classmethod
    @field_validator('final_amount')
    def validate_final_amount(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        # Truy cập giá trị các field khác
        if info.data:
            total = info.data.get('total_amount')
            shipping = info.data.get('shipping_fee')
            if total is not None and shipping is not None:
                expected = total + shipping
                if abs(v - expected) > Decimal('0.01'):
                    raise ValueError(
                        f'final_amount ({v}) phải bằng total_amount ({total}) + shipping_fee ({shipping}) = {expected}'
                    )
        return v

class UpdateOrderStatusRequest(BaseModel):
    order_status: OrderStatusEnum

class BuyNowRequest(BaseModel):
    """Request mua ngay sản phẩm"""
    product_id: int = Field(..., gt=0, description="ID sản phẩm")
    quantity: int = Field(..., gt=0, le=100, description="Số lượng")
    shipping_address: str = Field(..., min_length=5, description="Địa chỉ giao hàng")
    shipping_phone: str = Field(..., min_length=10, max_length=15, description="Số điện thoại nhận hàng")
    payment_method: PaymentMethodEnum = Field(..., description="Phương thức thanh toán")
    color_id: Optional[int] = Field(None, description="ID màu sắc")
    size_id: Optional[int] = Field(None, description="ID kích thước")
    shipping_fee: Optional[Decimal] = Field(Decimal('0'), description="Phí vận chuyển")
    customer_note: Optional[str] = Field(None, max_length=500, description="Ghi chú của khách hàng")