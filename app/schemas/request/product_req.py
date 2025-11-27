from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal

class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., max_length=255)
    category_id: Optional[int] = None
    price: Decimal = Field(..., gt=0)

class UpdateProductRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, gt=0)

class CreateProductDetailRequest(BaseModel):
    product_id: int
    packaging_type_id: Optional[int] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    usage: Optional[dict] = None
    benefits: Optional[dict] = None
    storage: Optional[str] = None

class UpdateProductDetailRequest(BaseModel):
    packaging_type_id: Optional[int] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    usage: Optional[dict] = None
    benefits: Optional[dict] = None
    storage: Optional[str] = None

class CreateProductImageRequest(BaseModel):
    product_id: int
    product_detail_id: Optional[int] = None
    image_url: str
    is_main: bool = False
    display_order: int = 0

class CreateProductColorRequest(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    stock: int = Field(default=0, ge=0)

class CreateProductSizeRequest(BaseModel):
    name: str = Field(..., max_length=20)

class CreatePackagingTypeRequest(BaseModel):
    name: str = Field(..., max_length=20)