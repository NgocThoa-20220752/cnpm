from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int]
    description: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryWithChildrenResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int]
    description: Optional[str]
    display_order: int
    created_at: datetime
    updated_at: datetime
    children: List['CategoryResponse']

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[CategoryResponse]

CategoryWithChildrenResponse.model_rebuild()