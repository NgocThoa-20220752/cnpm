from typing import cast

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.request.cart_req import AddToCartRequest, UpdateCartItemRequest, CheckoutRequest
from app.schemas.response.cart_resp import CartResponse
from app.schemas.response.auth_resp import MessageResponse
from app.services.cart_service import CartService
from app.Dependencies import get_current_customer, get_cart_service, get_order_service
from app.models.user import User
from app.models.customer import Customer
from app.exceptions import NotFoundException, InsufficientStockException, BadRequestException
from app.services.order_service import OrderService

router = APIRouter(prefix="/cart", tags=["cart"])

# lấy thông tin customer từ user đã đăng nhập
def get_current_customer_obj(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db)
) -> Customer:
    """Get customer object from current user"""
    customer = db.query(Customer).filter_by(id= current_user.id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return cast(Customer,customer)

@router.get(
    "",
    response_model=CartResponse,
    summary="Get cart",
    description="Retrieve the current customer's shopping cart"
)
async def get_cart(
    customer: Customer = Depends(get_current_customer_obj),
    db: Session = Depends(get_db)
):
    """Get customer's cart"""
    cart_service = CartService(db)
    return cart_service.get_cart(customer.id)

@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add to cart",
    description="Add a product to the shopping cart"
)
async def add_to_cart(
    request: AddToCartRequest,
    customer: Customer = Depends(get_current_customer_obj),
    db: Session = Depends(get_db)
):
    """Add item to cart"""
    cart_service = CartService(db)
    try:
        return cart_service.add_to_cart(customer.id, request)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientStockException as e:
        # GIỮ NGUYÊN 400 hoặc đổi thành 409 tùy bạn
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put(
    "/items/{cart_item_id}",
    response_model=CartResponse,
    summary="Update cart item",
    description="Update the quantity of a cart item"
)
async def update_cart_item(
    cart_item_id: int,
    request: UpdateCartItemRequest,
    customer: Customer = Depends(get_current_customer_obj),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    cart_service = CartService(db)
    try:
        return cart_service.update_cart_item(customer.id, cart_item_id, request)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientStockException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete(
    "/items/{cart_item_id}",
    response_model=CartResponse,
    summary="Remove from cart",
    description="Remove an item from the shopping cart"
)
async def remove_from_cart(
    cart_item_id: int,
    customer: Customer = Depends(get_current_customer_obj),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    cart_service = CartService(db)
    try:
        return cart_service.remove_from_cart(customer.id, cart_item_id)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.delete(
    "",
    response_model=MessageResponse,
    summary="Clear cart",
    description="Remove all items from the shopping cart"
)
async def clear_cart(
    customer: Customer = Depends(get_current_customer_obj),
    db: Session = Depends(get_db)
):
    """Clear cart"""
    cart_service = CartService(db)
    return cart_service.clear_cart(customer.id)


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout_cart(
        request: CheckoutRequest,
        current_user: User = Depends(get_current_customer),
        cart_service: CartService = Depends(get_cart_service),
        order_service: OrderService = Depends(get_order_service),
        db: Session = Depends(get_db)
):
    """
    Checkout từ giỏ hàng → tạo đơn hàng
    """
    try:
        print(f"🛒 Checkout request from user {current_user.id}")
        print(f"📦 Selected items: {request.selected_items}")

        # Gọi checkout TRỰC TIẾP với CheckoutRequest object
        result = cart_service.checkout(
            customer_id=current_user.id,
            checkout_request=request,  # TRUYỀN CheckoutRequest object
            order_service=order_service
        )

        print(f"✅ Checkout successful, order created")

        return {
            "success": True,
            "message": "Đã tạo đơn hàng thành công",
            "data": result
        }

    except BadRequestException as e:
        print(f"❌ BadRequest: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Checkout error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")