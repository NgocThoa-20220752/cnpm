from pydantic import BaseModel, Field

class AddToCartRequest(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., gt=0)