from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.enum import PaymentMethodEnum


class AddToCartRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    color_id: Optional[int] = Field(None)
    size_id: Optional[int] = Field(None)

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0)
    color_id: Optional[int] = Field(None)
    size_id: Optional[int] = Field(None)

    @classmethod
    @field_validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Số lượng phải lớn hơn 0')
        return v


class CheckoutRequest(BaseModel):
    shipping_address: str = Field(..., min_length=5)
    shipping_phone: str = Field(..., min_length=10, max_length=15)
    payment_method: PaymentMethodEnum
    shipping_fee: Optional[Decimal] = Field(Decimal('0'))
    customer_note: Optional[str] = Field(None, max_length=500)

    # THÊM: Danh sách cart_item_id được chọn
    selected_items: Optional[List[int]] = Field(None)

    @classmethod
    @field_validator('selected_items')
    def validate_selected_items(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None and len(v) == 0:
            raise ValueError('selected_items không được rỗng')
        return v