from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class ProductColorResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    stock: int

    class Config:
        from_attributes = True


class ProductSizeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class PackagingTypeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ProductImageResponse(BaseModel):
    id: int
    image_url: str
    is_main: bool
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductDetailResponse(BaseModel):
    id: int
    description: Optional[str]
    ingredients: Optional[str]
    usage: Optional[dict]
    benefits: Optional[dict]
    storage: Optional[str]
    packaging_type: Optional[PackagingTypeResponse]
    color: Optional[ProductColorResponse]
    size: Optional[ProductSizeResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    category: Optional[ProductCategoryResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductFullDetailResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    category: Optional[ProductCategoryResponse]
    product_details: List[ProductDetailResponse]
    images: List[ProductImageResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[ProductResponse]


class LowStockProductResponse(BaseModel):
    product_id: int
    product_name: str
    color_id: int
    color_name: str
    stock: int
    threshold: int = 10  # Ngưỡng cảnh báo tồn kho thấp

    class Config:
        from_attributes = True