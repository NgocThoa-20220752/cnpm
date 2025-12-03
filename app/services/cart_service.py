from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductDetail
from app.schemas.request.cart_req import AddToCartRequest, UpdateCartItemRequest
from app.exceptions import NotFoundException, InsufficientStockException
from decimal import Decimal


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_cart(self, customer_id: int) -> Cart:
        """Lấy hoặc tạo giỏ hàng"""
        cart = self.db.query(Cart).filter_by(customer_id=customer_id).first()
        if cart:
            return cart

        cart = Cart(customer_id=customer_id)
        self.db.add(cart)
        self.db.flush()
        self.db.refresh(cart)
        return cart

    def get_cart(self, customer_id: int):
        """Lấy thông tin giỏ hàng"""
        cart = self.get_or_create_cart(customer_id)

        # Lấy items với product info
        items = self.db.query(CartItem).filter_by(cart_id=cart.id).options(
            joinedload(CartItem.product)
        ).all()

        # Tính toán
        cart_items = []
        total_items = 0
        total_amount = Decimal('0')

        for item in items:
            # Tính subtotal
            subtotal = item.product.price * item.quantity

            # Lấy hình ảnh chính
            main_image = None
            if hasattr(item.product, 'images') and item.product.images:
                for img in item.product.images:
                    if img.is_main:
                        main_image = img.image_url
                        break

            # Lấy tổng stock từ tất cả variants
            total_stock = self.db.query(ProductDetail).filter_by(
                product_id=item.product_id
            ).with_entities(
                func.sum(ProductDetail.stock)
            ).scalar() or 0

            cart_items.append({
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "price": item.product.price,
                    "image_url": main_image,
                    "stock": total_stock,
                    "is_available": total_stock > 0
                },
                "subtotal": subtotal
            })

            total_items += item.quantity
            total_amount += subtotal

        return {
            "id": cart.id,
            "customer_id": cart.customer_id,
            "cart_items": cart_items,
            "total_items": total_items,
            "total_amount": total_amount,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at
        }

    def add_to_cart(self, customer_id: int, request: AddToCartRequest):
        """Thêm sản phẩm vào giỏ hàng"""
        try:
            cart = self.get_or_create_cart(customer_id)

            # Kiểm tra sản phẩm tồn tại
            product = self.db.query(Product).filter_by(id=request.product_id).first()
            if not product:
                raise NotFoundException("Product not found")

            # Kiểm tra số lượng
            if request.quantity <= 0:
                raise ValueError("Quantity must be greater than 0")

            # Kiểm tra tồn kho (tổng stock của tất cả variants)
            total_stock = self.db.query(ProductDetail).filter_by(
                product_id=request.product_id
            ).with_entities(
                func.sum(ProductDetail.stock)
            ).scalar() or 0

            # Kiểm tra item đã có trong giỏ chưa
            cart_item = self.db.query(CartItem).filter_by(
                cart_id=cart.id,
                product_id=request.product_id
            ).first()

            if cart_item:
                # Nếu đã có, cộng thêm số lượng
                new_quantity = cart_item.quantity + request.quantity

                # Kiểm tra stock
                if total_stock < new_quantity:
                    raise InsufficientStockException(
                        f"Insufficient stock. Available: {total_stock}"
                    )

                cart_item.quantity = new_quantity
            else:
                # Kiểm tra stock cho item mới
                if total_stock < request.quantity:
                    raise InsufficientStockException(
                        f"Insufficient stock. Available: {total_stock}"
                    )

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
        """Cập nhật số lượng sản phẩm"""
        try:
            cart = self.get_or_create_cart(customer_id)

            # Tìm cart item
            cart_item = self.db.query(CartItem).filter_by(
                id=cart_item_id,
                cart_id=cart.id
            ).first()

            if not cart_item:
                raise NotFoundException("Cart item not found")

            # Kiểm tra số lượng
            if request.quantity <= 0:
                raise ValueError("Quantity must be greater than 0")

            # Kiểm tra tồn kho
            total_stock = self.db.query(ProductDetail).filter_by(
                product_id=cart_item.product_id
            ).with_entities(
                func.sum(ProductDetail.stock)
            ).scalar() or 0

            if total_stock < request.quantity:
                raise InsufficientStockException(
                    f"Insufficient stock. Available: {total_stock}"
                )

            cart_item.quantity = request.quantity
            self.db.commit()

            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def remove_from_cart(self, customer_id: int, cart_item_id: int):
        """Xóa sản phẩm khỏi giỏ hàng"""
        try:
            cart = self.get_or_create_cart(customer_id)

            cart_item = self.db.query(CartItem).filter_by(
                id=cart_item_id,
                cart_id=cart.id
            ).first()

            if not cart_item:
                raise NotFoundException("Cart item not found")

            self.db.delete(cart_item)
            self.db.commit()

            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def clear_cart(self, customer_id: int):
        """Xóa toàn bộ giỏ hàng"""
        try:
            cart = self.get_or_create_cart(customer_id)

            if cart.id:
                self.db.query(CartItem).filter_by(cart_id=cart.id).delete()
                self.db.commit()

            return {"message": "Cart cleared successfully"}

        except Exception:
            self.db.rollback()
            raise