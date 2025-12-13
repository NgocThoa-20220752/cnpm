from typing import Optional, List

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductDetail
from app.schemas.request.cart_req import AddToCartRequest, UpdateCartItemRequest, CheckoutRequest
from app.exceptions import NotFoundException, InsufficientStockException, BadRequestException
from decimal import Decimal

from app.schemas.request.order_req import OrderItemRequest, CreateOrderRequest
from app.services.order_service import OrderService


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
            # ✅ SỬA: Tìm variant để lấy giá thực
            variant = self._get_product_detail(
                item.product_id,
                item.color_id,
                item.size_id
            )

            # Lấy giá từ variant
            price = variant.price if variant and variant.price is not None else Decimal('0')

            # Tính subtotal với giá đúng
            subtotal = price * item.quantity

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
                "color_id": item.color_id,
                "size_id": item.size_id,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "slug": item.product.slug,
                    "price": price,  # ✅ Dùng giá từ variant
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
        """Thêm sản phẩm vào giỏ hàng với màu/size"""
        try:
            cart = self.get_or_create_cart(customer_id)

            product = self.db.query(Product).get(request.product_id)
            if not product:
                raise NotFoundException("Product not found")

            # Kiểm tra variant tồn tại (nếu chọn màu/size)
            if request.color_id or request.size_id:
                variant = self._get_product_detail(
                    request.product_id,
                    request.color_id,
                    request.size_id
                )
                if not variant:
                    raise NotFoundException("Màu/Size không tồn tại cho sản phẩm này")

            # Kiểm tra số lượng
            if request.quantity <= 0:
                raise ValueError("Quantity must be greater than 0")

            # KIỂM TRA STOCK - THÊM ĐOẠN NÀY ↓
            from sqlalchemy import func
            total_stock = self.db.query(ProductDetail).filter_by(
                product_id=request.product_id
            ).with_entities(
                func.sum(ProductDetail.stock)
            ).scalar() or 0

            # Tìm cart item cùng product VÀ cùng màu/size
            cart_item = self.db.query(CartItem).filter_by(
                cart_id=cart.id,
                product_id=request.product_id,
                color_id=request.color_id,
                size_id=request.size_id
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
                    quantity=request.quantity,
                    color_id=request.color_id,  # THÊM
                    size_id=request.size_id  # THÊM
                )
                self.db.add(cart_item)

            self.db.commit()
            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def update_cart_item(self, customer_id: int, cart_item_id: int, request: UpdateCartItemRequest):
        """Cập nhật cart item (có thể đổi màu/size)"""
        try:
            cart = self.get_or_create_cart(customer_id)

            cart_item = self.db.query(CartItem).filter_by(
                id=cart_item_id,
                cart_id=cart.id
            ).first()

            if not cart_item:
                raise NotFoundException("Cart item not found")

            # Cập nhật số lượng (nếu có)
            if request.quantity is not None:
                if request.quantity <= 0:
                    raise ValueError("Số lượng phải lớn hơn 0")

                # GỌI HÀM KIỂM TRA STOCK
                total_stock = self._get_product_stock(cart_item.product_id)

                if total_stock < request.quantity:
                    raise InsufficientStockException(f"Không đủ tồn kho: {total_stock}")

                cart_item.quantity = request.quantity

            # Cập nhật màu (nếu có)
            if request.color_id is not None:
                cart_item.color_id = request.color_id

            # Cập nhật size (nếu có)
            if request.size_id is not None:
                cart_item.size_id = request.size_id

            # Kiểm tra variant tồn tại (nếu đổi màu/size)
            if request.color_id is not None or request.size_id is not None:
                variant = self._get_product_detail(
                    cart_item.product_id,
                    request.color_id or cart_item.color_id,
                    request.size_id or cart_item.size_id
                )
                if not variant:
                    raise NotFoundException("Màu/Size không tồn tại cho sản phẩm này")

            self.db.commit()
            return self.get_cart(customer_id)

        except Exception:
            self.db.rollback()
            raise

    def _get_product_stock(self, product_id: int) -> int:
        """Lấy tổng stock của product (từ tất cả variants)"""
        from sqlalchemy import func
        from app.models.product import ProductDetail

        total_stock = self.db.query(ProductDetail).filter_by(
            product_id=product_id
        ).with_entities(
            func.sum(ProductDetail.stock)
        ).scalar() or 0

        return total_stock

    def _get_product_detail(self, product_id: int, color_id: Optional[int], size_id: Optional[int]) -> Optional[
        ProductDetail]:
        """Tìm product detail (variant) của sản phẩm"""
        query = self.db.query(ProductDetail).filter_by(product_id=product_id)

        if color_id and size_id:
            return query.filter_by(color_id=color_id, size_id=size_id).first()
        elif color_id:
            return query.filter_by(color_id=color_id).first()
        elif size_id:
            return query.filter_by(size_id=size_id).first()
        else:
            return query.first()  # Lấy variant đầu tiên nếu không có color/size

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

    def checkout(self, customer_id: int, checkout_request: CheckoutRequest, order_service: OrderService) -> dict:
        from decimal import Decimal

        try:
            # 1. Validate shipping info
            required_fields = ["shipping_address", "shipping_phone", "payment_method"]
            for field in required_fields:
                if not getattr(checkout_request, field, None):
                    raise BadRequestException(f"Thiếu thông tin bắt buộc: {field}")

            # 2. Lấy và lock cart để tránh race condition
            cart = self.get_or_create_cart(customer_id)

            # FOR UPDATE lock để đảm bảo không có concurrent checkout
            self.db.query(Cart).filter(Cart.id == cart.id).with_for_update().first()

            # 3. Lấy cart items từ database (không dùng get_cart vì có cache/transform)
            cart_items = self.db.query(CartItem).filter(
                CartItem.cart_id == cart.id
            ).options(
                joinedload(CartItem.product)
            ).all()

            if not cart_items:
                raise BadRequestException("Giỏ hàng trống")

            # 4. Lọc cart items theo selected_items
            cart_items_to_checkout = []
            if checkout_request.selected_items:
                # Chỉ lấy các items được chọn
                selected_ids_set = set(checkout_request.selected_items)
                for item in cart_items:
                    if item.id in selected_ids_set:
                        cart_items_to_checkout.append(item)
            else:
                # Nếu không có selected_items, checkout toàn bộ
                cart_items_to_checkout = cart_items

            if not cart_items_to_checkout:
                raise BadRequestException("Không có sản phẩm nào được chọn để thanh toán")

            # 5. Tính toán tổng tiền và KIỂM TRA STOCK
            order_items = []
            total_amount = Decimal("0")

            for cart_item in cart_items_to_checkout:
                # Lấy variant cụ thể
                variant = self._get_product_detail(
                    cart_item.product_id,
                    cart_item.color_id,
                    cart_item.size_id
                )

                if not variant:
                    raise NotFoundException(f"Không tìm thấy variant cho sản phẩm {cart_item.product_id}")

                if variant.price is None:
                    raise ValueError(f"Variant {variant.id} không có giá")

                # Kiểm tra stock cụ thể của variant
                if variant.stock < cart_item.quantity:
                    product_name = cart_item.product.name if cart_item.product else f"ID:{cart_item.product_id}"
                    raise InsufficientStockException(
                        f"Sản phẩm {product_name} chỉ còn {variant.stock} sản phẩm"
                    )

                # Tính tiền
                product_price = Decimal(str(variant.price))
                item_total = product_price * Decimal(str(cart_item.quantity))
                total_amount += item_total

                order_items.append(
                    OrderItemRequest(
                        product_id=cart_item.product_id,
                        quantity=cart_item.quantity,
                        color_id=cart_item.color_id,
                        size_id=cart_item.size_id,
                        price=product_price
                    )
                )

            # 6. Tính tổng cuối cùng với shipping fee
            shipping_fee = Decimal(str(checkout_request.shipping_fee or 0))
            if shipping_fee < 0:
                raise BadRequestException("Phí vận chuyển không hợp lệ")

            final_amount = total_amount + shipping_fee

            # 7. Tạo order request
            order_request = CreateOrderRequest(
                items=order_items,
                shipping_address=checkout_request.shipping_address,
                shipping_phone=checkout_request.shipping_phone,
                payment_method=checkout_request.payment_method,
                shipping_fee=shipping_fee,
                customer_note=checkout_request.customer_note or "",
                total_amount=total_amount,
                final_amount=final_amount
            )

            # 8. Gọi service tạo order
            result = order_service.create_order(customer_id, order_request)

            # 9. Nếu tạo order thành công, xóa items đã checkout khỏi giỏ hàng
            if result.get("order"):
                self._remove_checkout_items(customer_id, checkout_request.selected_items, cart)

            # 10. COMMIT transaction - QUAN TRỌNG!
            self.db.commit()
            return result

        except Exception as e:
            # Rollback transaction khi có lỗi
            self.db.rollback()
            raise

    def _remove_checkout_items(self, customer_id: int, selected_item_ids: Optional[List[int]], cart: Cart = None):
        """Xóa các items đã checkout khỏi giỏ hàng"""
        if not cart:
            cart = self.get_or_create_cart(customer_id)

        try:
            if selected_item_ids:
                # Chỉ xóa các items được chọn
                self.db.query(CartItem).filter(
                    CartItem.cart_id == cart.id,
                    CartItem.id.in_(selected_item_ids)
                ).delete()
            else:
                # Xóa toàn bộ giỏ hàng
                self.db.query(CartItem).filter(
                    CartItem.cart_id == cart.id
                ).delete()

            # KHÔNG commit ở đây, commit sẽ được gọi ở checkout()

        except Exception as e:
            # Log lỗi nhưng không rollback - để checkout() xử lý
            # (hoặc có thể re-raise để checkout() rollback toàn bộ)
            raise
