from pydantic import BaseModel, Field
from typing import Optional

class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., max_length=100)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    display_order: int = Field(default=0)

class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    display_order: Optional[int] = None