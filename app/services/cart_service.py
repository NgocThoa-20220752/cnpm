from sqlalchemy.orm import Session
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.request.cart_req import AddToCartRequest, UpdateCartItemRequest
from app.exceptions import NotFoundException, InsufficientStockException
from decimal import Decimal


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_cart(self, customer_id: int) -> Cart:
        cart = self.db.query(Cart).filter_by(customer_id=customer_id).first()

        if cart:
            return cart

        cart = Cart(customer_id=customer_id)
        self.db.add(cart)
        self.db.flush()  # đảm bảo cart.id được sinh nhưng chưa commit
        self.db.refresh(cart)
        return cart

    def get_cart(self, customer_id: int):
        """Get customer's cart with items"""
        cart = self.db.query(Cart).filter_by(customer_id=customer_id).first()

        if not cart:
            return {
                "id": None,
                "customer_id": customer_id,
                "cart_items": [],
                "total_items": 0,
                "total_amount": Decimal('0'),
                "created_at": None,
                "updated_at": None
            }

        # Calculate totals
        total_items = 0
        total_amount = Decimal('0')
        cart_items_with_subtotal = []

        for item in cart.cart_items:
            total_items += item.quantity
            subtotal = item.product.price * item.quantity
            total_amount += subtotal

            # Tạo cart item với subtotal
            cart_item_data = {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "product": item.product,
                "subtotal": subtotal
            }
            cart_items_with_subtotal.append(cart_item_data)

        return {
            "id": cart.id,
            "customer_id": cart.customer_id,
            "cart_items": cart_items_with_subtotal,  # DÙNG list mới có subtotal
            "total_items": total_items,
            "total_amount": total_amount,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at  # THÊM updated_at
        }

    def add_to_cart(self, customer_id: int, request: AddToCartRequest):
        try:
            cart = self.get_or_create_cart(customer_id)

            if request.quantity <= 0:
                raise ValueError("Quantity must be greater than 0")

            product = self.db.query(Product).filter_by(id=request.product_id).first()
            if not product:
                raise NotFoundException("Product not found")

            cart_item = self.db.query(CartItem).filter_by(
                cart_id=cart.id, product_id=request.product_id
            ).first()

            if cart_item:
                cart_item.quantity += request.quantity
            else:
                cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=request.product_id,
                    quantity=request.quantity
                )
                self.db.add(cart_item)

            self.db.commit()
            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def update_cart_item(self, customer_id: int, cart_item_id: int, request: UpdateCartItemRequest):
        """Update cart item quantity"""
        try:
            cart = self.get_or_create_cart(customer_id)

            cart_item = self.db.query(CartItem).filter_by(
                id=cart_item_id,
                cart_id=cart.id
            ).first()

            if not cart_item:
                raise NotFoundException("Cart item not found")

            # Validate quantity
            if request.quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
            cart_item.quantity = request.quantity
            self.db.commit()

            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def remove_from_cart(self, customer_id: int, cart_item_id: int):
        try:
            cart = self.get_or_create_cart(customer_id)

            cart_item = self.db.query(CartItem).filter_by(id=cart_item_id, cart_id=cart.id).first()
            if not cart_item:
                raise NotFoundException("Cart item not found")

            self.db.delete(cart_item)
            self.db.commit()

            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def clear_cart(self, customer_id: int):
        try:
            cart = self.get_or_create_cart(customer_id)

            if cart.id:
                self.db.query(CartItem).filter_by(cart_id=cart.id).delete()
                self.db.commit()

            return {"message": "Cart cleared successfully"}

        except Exception:
            self.db.rollback()
            raise
