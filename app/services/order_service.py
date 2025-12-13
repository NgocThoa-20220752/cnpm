from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import Optional, List, cast, Dict
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
from contextlib import contextmanager
import logging

from fastapi import Request

from app.core.config import get_settings
from app.models import Customer
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductDetail
from app.models.user import User
from app.schemas.request.order_req import CreateOrderRequest, UpdateOrderStatusRequest, OrderItemRequest
from app.exceptions import (
    NotFoundException, BadRequestException,
    InsufficientStockException, OrderCancellationException
)
from app.enum import OrderStatusEnum, PaymentStatusEnum, PaymentMethodEnum
from app.core.email import EmailService
from app.services.payment_service import RealPaymentService

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(self, db: Session, request: Optional[Request] = None):
        self.db = db
        self.settings = get_settings()

        client_ip = "127.0.0.1"
        if request and hasattr(request, 'client') and request.client:
            client_ip = request.client.host

        self.payment_service = RealPaymentService(
            settings=self.settings,
            is_production=False,
            request_ip=client_ip
        )
        self._setup_valid_status_transitions()

    # quy tắc chuyển đổi trạng thái đơn hàng
    def _setup_valid_status_transitions(self) -> None:
        """Setup valid status transitions"""
        self.valid_transitions = {
            OrderStatusEnum.PENDING: [OrderStatusEnum.CONFIRMED, OrderStatusEnum.CANCELLED],
            OrderStatusEnum.CONFIRMED: [OrderStatusEnum.PROCESSING, OrderStatusEnum.CANCELLED],
            OrderStatusEnum.PROCESSING: [OrderStatusEnum.SHIPPED, OrderStatusEnum.CANCELLED],
            OrderStatusEnum.SHIPPED: [OrderStatusEnum.DELIVERED],
            OrderStatusEnum.DELIVERED: [OrderStatusEnum.RETURN_REQUESTED],
            OrderStatusEnum.RETURN_REQUESTED: [OrderStatusEnum.RETURN_APPROVED, OrderStatusEnum.RETURN_REJECTED],
            OrderStatusEnum.RETURN_APPROVED: [OrderStatusEnum.RETURNED, OrderStatusEnum.REFUNDED],
            OrderStatusEnum.RETURN_REJECTED: [OrderStatusEnum.DELIVERED],
            OrderStatusEnum.RETURNED: [],
            OrderStatusEnum.REFUNDED: [],
            OrderStatusEnum.CANCELLED: []
        }

        self.cancellable_statuses = [
            OrderStatusEnum.PENDING,
            OrderStatusEnum.CONFIRMED,
            OrderStatusEnum.PROCESSING
        ]

    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        try:
            yield self.db
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Transaction failed: {str(e)}")
            raise

    @staticmethod
    def generate_order_code() -> str:
        """Generate unique order code"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = str(uuid.uuid4())[:8].upper()
        return f"ORD{timestamp}{random_str}"

    # ==================== STOCK MANAGEMENT ====================
    #
    def _get_product_detail(self, product_id: int, color_id: Optional[int], size_id: Optional[int]) -> Optional[
        ProductDetail]:
        """Get product detail với fallback"""
        query = self.db.query(ProductDetail).filter_by(product_id=product_id)

        if color_id is None and size_id is None:
            variant = query.filter(
                ProductDetail.color_id.is_(None),
                ProductDetail.size_id.is_(None)
            ).first()
            if variant:
                return cast(Optional[ProductDetail], variant)

        if color_id is not None and size_id is not None:
            variant = query.filter_by(color_id=color_id, size_id=size_id).first()
            if variant:
                return cast(Optional[ProductDetail], variant)

        if size_id is not None and color_id is None:
            variant = query.filter_by(size_id=size_id, color_id=None).first()
            if variant:
                return cast(Optional[ProductDetail], variant)

        if color_id is not None and size_id is None:
            variant = query.filter_by(color_id=color_id, size_id=None).first()
            if variant:
                return cast(Optional[ProductDetail], variant)

        return query.first()

    # Kiểm tra stock trước khi tạo đơn
    def check_stock_availability(self, items: List[OrderItemRequest]) -> bool:
        """Check stock availability for all order items"""
        for item in items:
            product_detail = self._get_product_detail(item.product_id, item.color_id, item.size_id)

            if not product_detail:
                raise NotFoundException(f"Product variant not found for product {item.product_id}")

            if product_detail.stock < item.quantity:
                raise InsufficientStockException(
                    f"Insufficient stock: Available {product_detail.stock}, Requested {item.quantity}"
                )
        return True
    # Trừ stock khi xác nhận đơn
    def _deduct_stock_for_items(self, items: List[OrderItemRequest]) -> None:
        """Deduct stock for list of items"""
        for item in items:
            product_detail = self._get_product_detail(item.product_id, item.color_id, item.size_id)

            if not product_detail:
                raise NotFoundException(f"Product variant not found")

            if product_detail.stock < item.quantity:
                raise InsufficientStockException(
                    f"Insufficient stock for product {item.product_id}"
                )

            product_detail.stock -= item.quantity
            logger.info(f"Reduced stock for product detail {product_detail.id}: -{item.quantity}")

    # Hoàn lại stock khi hủy/trả hàng
    def _restore_stock_for_items(self, order_items: List[OrderItem]) -> None:
        """Restore stock from order items"""
        for order_item in order_items:
            if order_item.product_detail_id:
                product_detail = self.db.query(ProductDetail).get(order_item.product_detail_id)
                if product_detail:
                    product_detail.stock += order_item.quantity
                    logger.info(f"Restored stock for product detail {product_detail.id}: +{order_item.quantity}")

    # ==================== ORDER CREATION ====================

    def create_order(self, customer_id: int, request: CreateOrderRequest,
                     payment_data: Optional[dict] = None) -> dict:
        """Create new order"""
        logger.info(f"Creating order for customer {customer_id}")

        if not request.items:
            raise BadRequestException("Order must have at least one item")

        self.check_stock_availability(request.items)

        with self.transaction():
            order, order_items_data = self._prepare_order_data(customer_id, request)
            self.db.add(order)
            self.db.flush()

            self._create_order_items(order.id, order_items_data)

            payment_result = None
            if request.payment_method in [PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY]:
                payment_result = self._create_online_payment(order, request, payment_data)

        self._send_order_confirmation_email(customer_id, order.order_code, float(order.total_amount))

        return {
            "order": order,
            "payment_result": payment_result
        }

    def _prepare_order_data(self, customer_id: int, request: CreateOrderRequest) -> tuple:
        """Prepare order data"""
        calculated_total = Decimal('0')
        items_with_data = []

        for item in request.items:
            product = self.db.query(Product).get(item.product_id)
            if not product:
                raise NotFoundException(f"Product {item.product_id} not found")

            product_detail = self._get_product_detail(item.product_id, item.color_id, item.size_id)
            if not product_detail:
                raise NotFoundException(f"Product variant not found for product {item.product_id}")

            if product_detail.price is None:
                raise ValueError(f"Variant {product_detail.id} không có giá")

            unit_price = Decimal(str(product_detail.price))
            product_name = product.name
            product_detail_id = product_detail.id

            subtotal = unit_price * item.quantity
            calculated_total += subtotal

            items_with_data.append({
                "item": item,
                "unit_price": unit_price,
                "product_name": product_name,
                "product_detail_id": product_detail_id,
                "subtotal": subtotal
            })

        tolerance = Decimal('0.01')
        if abs(calculated_total - request.total_amount) > tolerance:
            error_msg = f"Total amount mismatch: calculated={calculated_total}, requested={request.total_amount}"
            logger.error(error_msg)
            raise BadRequestException(error_msg)

        order = Order(
            order_code=self.generate_order_code(),
            customer_id=customer_id,
            total_amount=request.total_amount,
            shipping_fee=request.shipping_fee or Decimal('0'),
            final_amount=request.final_amount,
            payment_method=request.payment_method,
            payment_status=PaymentStatusEnum.PENDING,
            order_status=OrderStatusEnum.PENDING,
            shipping_address=request.shipping_address,
            shipping_phone=request.shipping_phone,
            note=request.customer_note
        )

        return order, items_with_data

    def _create_order_items(self, order_id: int, items_with_data: List[dict]) -> None:
        """Create order items"""
        for data in items_with_data:
            item = data["item"]
            unit_price = data["unit_price"]
            product_name = data["product_name"]
            product_detail_id = data["product_detail_id"]
            subtotal = data["subtotal"]

            order_item = OrderItem(
                order_id=order_id,
                product_id=item.product_id,
                product_detail_id=product_detail_id,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                product_name=product_name
            )
            self.db.add(order_item)

    def _create_online_payment(self, order: Order, request: CreateOrderRequest,
                               payment_data: Optional[dict]) -> Optional[dict]:
        """Create online payment"""
        try:
            payment_result = self.payment_service.create_payment(
                method=request.payment_method.value,
                order_id=order.id,
                order_code=order.order_code,
                amount=order.total_amount,
                order_info=f"Payment for order {order.order_code}",
                bank_code=payment_data.get("bank_code") if payment_data else None
            )

            if not payment_result.get("success"):
                logger.error(f"Payment creation failed: {payment_result.get('error')}")
                raise BadRequestException(f"Payment creation failed: {payment_result.get('error')}")

            return payment_result

        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}")
            raise BadRequestException(f"Payment processing failed: {str(e)}")

    # ==================== ORDER STATUS MANAGEMENT ====================

    def confirm_cod_order_and_deduct_stock(self, order_id: int) -> Order:
        """Confirm COD order and deduct stock"""
        logger.info(f"Confirming COD order {order_id} and deducting stock")

        with self.transaction():
            order = self._get_order(order_id)

            if order.order_status != OrderStatusEnum.PENDING:
                raise BadRequestException("Only pending orders can be confirmed")

            if order.payment_method != PaymentMethodEnum.CASH:
                raise BadRequestException("Only COD orders can use this method")

            items_to_deduct = self._prepare_items_for_stock_deduction(order)
            self._deduct_stock_for_items(items_to_deduct)
            logger.info(f"Stock deducted for COD order {order_id}")

            order.order_status = OrderStatusEnum.CONFIRMED

        return order


    def confirm_order(self, order_id: int) -> Order:
        """Confirm order (Admin confirms pending order)"""
        logger.info(f"Admin confirming order {order_id}")

        with self.transaction():
            order = self._get_order(order_id)

            if order.order_status != OrderStatusEnum.PENDING:
                raise BadRequestException("Only pending orders can be confirmed")

            # Nếu là COD, trừ stock ngay
            if order.payment_method == PaymentMethodEnum.CASH:
                items_to_deduct = self._prepare_items_for_stock_deduction(order)
                self._deduct_stock_for_items(items_to_deduct)

            order.order_status = OrderStatusEnum.CONFIRMED

        return order

    def _prepare_items_for_stock_deduction(self, order: Order) -> List[OrderItemRequest]:
        """Prepare items for stock deduction"""
        items_to_deduct = []
        for item in order.order_items:
            product_detail = self.db.query(ProductDetail).get(item.product_detail_id)
            if product_detail:
                items_to_deduct.append(
                    OrderItemRequest(
                        product_id=item.product_id,
                        color_id=product_detail.color_id,
                        size_id=product_detail.size_id,
                        quantity=item.quantity,
                        price=item.unit_price
                    )
                )
        return items_to_deduct

    def update_order_status(self, order_id: int, request: UpdateOrderStatusRequest) -> Order:
        """Update order status with validation"""
        logger.info(f"Updating order {order_id} status to: {request.order_status}")

        with self.transaction():
            order = self._get_order(order_id)

            new_status = self._validate_and_get_new_status(order.order_status, request.order_status)

            order.order_status = new_status

            self._handle_cod_payment_and_email(order, new_status)

        logger.info(f"Order {order_id} status updated to {new_status.value}")
        return order

    def _validate_and_get_new_status(self, current_status_str: str, new_status_str: str) -> OrderStatusEnum:
        """Validate status transition"""
        current_status = OrderStatusEnum(current_status_str)
        new_status = OrderStatusEnum(new_status_str)

        if new_status not in self.valid_transitions.get(current_status, []):
            raise BadRequestException(
                f"Cannot change status from {current_status.value} to {new_status.value}"
            )

        return new_status

    def _handle_cod_payment_and_email(self, order: Order, new_status: OrderStatusEnum) -> None:
        """Handle COD payment and send email"""
        if (new_status == OrderStatusEnum.DELIVERED and
                order.payment_method == PaymentMethodEnum.CASH and
                order.payment_status == PaymentStatusEnum.PENDING):
            order.payment_status = PaymentStatusEnum.PAID
            logger.info("Auto-updated COD payment to PAID")

            try:
                self._send_payment_confirmation_email(
                    order.customer_id,
                    order.order_code,
                    float(order.total_amount)
                )
            except Exception as e:
                logger.error(f"Failed to send COD payment confirmation email: {str(e)}")

    # ==================== ORDER CANCELLATION ====================

    def cancel_order(self, order_id: int, customer_id: int, reason: Optional[str] = None) -> Order:
        """Cancel order with permission check"""
        logger.info(f"Cancelling order {order_id} for customer {customer_id}")

        with self.transaction():
            order = self._get_order(order_id)
            self._validate_order_ownership(order, customer_id)
            self._validate_cancellable_status(order.order_status)

            if order.payment_method == PaymentMethodEnum.CASH:
                self._restore_stock_for_items(order.order_items)
                order.payment_status = PaymentStatusEnum.CANCELLED
            elif order.payment_status == PaymentStatusEnum.PAID:
                self._process_refund_for_cancellation(order, reason)
                self._restore_stock_for_items(order.order_items)

            order.order_status = OrderStatusEnum.CANCELLED
            if reason:
                order.cancellation_reason = reason

        return order

    def admin_cancel_order(self, order_id: int, reason: Optional[str] = None) -> Order:
        """Admin cancel order"""
        logger.info(f"Admin cancelling order {order_id}")

        with self.transaction():
            order = self._get_order(order_id)

            admin_cancellable = self.cancellable_statuses + [OrderStatusEnum.SHIPPED]
            self._validate_cancellable_status(order.order_status, admin_cancellable)

            if order.payment_method == PaymentMethodEnum.CASH:
                self._restore_stock_for_items(order.order_items)
                order.payment_status = PaymentStatusEnum.CANCELLED
            elif order.payment_status == PaymentStatusEnum.PAID:
                self._process_refund_for_cancellation(order, reason, is_admin=True)
                self._restore_stock_for_items(order.order_items)

            order.order_status = OrderStatusEnum.CANCELLED
            if reason:
                order.cancellation_reason = reason

        return order

    def _validate_order_ownership(self, order: Order, customer_id: int) -> None:
        """Validate order ownership"""
        if order.customer_id != customer_id:
            raise OrderCancellationException("You don't have permission to cancel this order")

    def _validate_cancellable_status(self, status_str: str, allowed_statuses: Optional[List] = None) -> None:
        """Validate if order can be cancelled"""
        if allowed_statuses is None:
            allowed_statuses = self.cancellable_statuses

        status = OrderStatusEnum(status_str)
        if status not in allowed_statuses:
            raise OrderCancellationException(f"Cannot cancel order at {status.value} stage")

    def _process_refund_for_cancellation(self, order: Order, reason: str, is_admin: bool = False) -> None:
        """Process refund for cancelled order"""
        if order.payment_method in [PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY]:
            refund_reason = f"{'Admin' if is_admin else 'Customer'} cancellation: {reason or 'No reason'}"

            refund_result = self.payment_service.process_refund(
                order_id=order.id,
                amount=order.total_amount,
                reason=refund_reason
            )

            if not refund_result.get("success"):
                raise OrderCancellationException(f"Refund failed: {refund_result.get('error')}")

            order.payment_status = PaymentStatusEnum.REFUNDED

    # ==================== ORDER QUERIES ====================

    def _get_order(self, order_id: int) -> Order:
        """Get order by ID"""
        order = self.db.query(Order).get(order_id)
        if not order:
            raise NotFoundException("Order not found")
        return cast(Order, order)

    def get_order_by_id(self, order_id: int) -> Order:
        """Public method to get order by ID"""
        return self._get_order(order_id)

    def get_order_by_code(self, order_code: str) -> Order:
        """Get order by code"""
        order = self.db.query(Order).filter_by(order_code=order_code).first()
        if not order:
            raise NotFoundException("Order not found")
        return cast(Order, order)

    def get_customer_orders(self, customer_id: int, page: int = 1, limit: int = 20,
                            search: Optional[str] = None, order_status: Optional[str] = None) -> dict:
        """Get customer's orders"""
        query = self.db.query(Order).filter_by(customer_id=customer_id)
        return self._paginate_and_filter_orders(query, page, limit, search, order_status)

    def get_all_orders(self, page: int = 1, limit: int = 20, search: Optional[str] = None,
                       order_status: Optional[str] = None, payment_status: Optional[str] = None) -> dict:
        """Get all orders with filters"""
        query = self.db.query(Order)

        if search:
            query = query.join(Customer).join(User).filter(
                or_(
                    Order.order_code.ilike(f"%{search}%"),
                    User.fullname.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        if payment_status:
            query = query.filter_by(payment_status=PaymentStatusEnum(payment_status))

        return self._paginate_and_filter_orders(query, page, limit, search, order_status)

    def _paginate_and_filter_orders(self, query, page: int, limit: int,
                                    search: Optional[str], order_status: Optional[str]) -> dict:
        """Paginate and filter orders"""
        if order_status:
            query = query.filter_by(order_status=OrderStatusEnum(order_status))

        query = query.order_by(Order.created_at.desc())
        total = query.count()
        orders = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": orders
        }

    def get_customer_orders_report(self, limit: int = 10) -> List[Dict]:
        """Get customers with most orders (Admin report)"""
        results = self.db.query(
            Customer.id,
            User.full_name,
            User.email,
            func.count(Order.id).label('total_orders'),
            func.sum(Order.total_amount).label('total_spent')
        ).join(User).join(Order).group_by(
            Customer.id, User.full_name, User.email
        ).order_by(
            func.count(Order.id).desc()
        ).limit(limit).all()

        return [
            {
                "customer_id": r.id,
                "customer_name": r.full_name or "N/A",
                "email": r.email,
                "total_orders": r.total_orders or 0,
                "total_spent": float(r.total_spent) if r.total_spent else 0.0
            }
            for r in results
        ]

    # ==================== ORDER ACTIONS ====================

    def request_order_return(self, order_id: int, customer_id: int, reason: str) -> dict:
        """Request order return"""
        logger.info(f"Customer {customer_id} requesting return for order {order_id}")

        with self.transaction():
            order = self._get_order(order_id)
            self._validate_order_ownership(order, customer_id)

            if order.order_status != OrderStatusEnum.DELIVERED:
                raise BadRequestException("Only delivered orders can be returned")

            if order.payment_status != PaymentStatusEnum.PAID:
                raise BadRequestException("Only paid orders can be returned")

            order.order_status = OrderStatusEnum.RETURN_REQUESTED

        return {
            "message": "Return request submitted",
            "reason": reason,
            "order_status": OrderStatusEnum.RETURN_REQUESTED.value
        }

    def confirm_order_receipt(self, order_id: int, customer_id: int) -> Order:
        """Customer confirms order receipt"""
        logger.info(f"Customer {customer_id} confirming receipt for order {order_id}")

        with self.transaction():
            order = self._get_order(order_id)
            self._validate_order_ownership(order, customer_id)

            if order.order_status != OrderStatusEnum.SHIPPED:
                raise BadRequestException("Only shipped orders can be confirmed as received")

            order.order_status = OrderStatusEnum.DELIVERED

            self._handle_cod_payment_and_email(order, OrderStatusEnum.DELIVERED)

        return order

    # ==================== PAYMENT HANDLING ====================

    def check_payment_status(self, order_id: int, customer_id: int) -> dict:
        """Check payment status"""
        order = self._get_order(order_id)

        if order.customer_id != customer_id:
            raise BadRequestException("Permission denied")

        response = {
            "order_id": order_id,
            "order_code": order.order_code,
            "payment_method": order.payment_method.value,
            "payment_status": order.payment_status.value,
            "order_status": order.order_status.value,
            "amount": float(order.total_amount),
            "checked_at": datetime.now().isoformat()
        }

        if order.payment_method in [PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY]:
            self._handle_online_payment_check(order, response)

        return response

    def _handle_online_payment_check(self, order: Order, response: dict) -> None:
        """Handle online payment status check"""
        payment_check = self.payment_service.check_payment_status(order.id)
        response.update({
            "gateway_status": payment_check.get("status"),
            "paid": payment_check.get("paid"),
            "gateway_message": payment_check.get("message")
        })

        if (payment_check.get("paid") and
                order.payment_status == PaymentStatusEnum.PENDING):
            with self.transaction():
                order.payment_status = PaymentStatusEnum.PAID
                self._send_payment_confirmation_email(
                    order.customer_id, order.order_code, float(order.total_amount)
                )
                response["payment_processed"] = True

    # ==================== WEBHOOK PROCESSING ====================
    # Xử lý callback từ cổng thanh toán
    def process_payment_webhook(self, gateway: str, data: dict) -> dict:
        """Process payment webhook"""
        logger.info(f"Processing {gateway} webhook")

        verification = self.payment_service.verify_payment_webhook(data, gateway)
        if not verification.get("valid"):
            return {"success": False, "error": "Invalid webhook data"}

        order_id = self._extract_order_id_from_webhook(gateway, data, verification)
        if not order_id:
            return {"success": False, "error": "Order ID not found"}

        try:
            with self.transaction():
                order = self.db.query(Order).with_for_update().get(order_id)
                if not order:
                    return {"success": False, "error": "Order not found"}

                if (verification.get("status") == "completed" and
                        order.payment_status != PaymentStatusEnum.PAID):

                    order.payment_status = PaymentStatusEnum.PAID

                    if (order.payment_method in [PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY] and
                            order.order_status == OrderStatusEnum.PENDING):

                        for order_item in order.order_items:
                            if order_item.product_detail_id:
                                product_detail = self.db.query(ProductDetail).with_for_update().get(
                                    order_item.product_detail_id
                                )
                                if not product_detail:
                                    raise NotFoundException(
                                        f"Product detail {order_item.product_detail_id} not found"
                                    )

                                if product_detail.stock < order_item.quantity:
                                    raise InsufficientStockException(
                                        f"Insufficient stock for product {order_item.product_id}: "
                                        f"Available {product_detail.stock}, Requested {order_item.quantity}"
                                    )

                                product_detail.stock -= order_item.quantity

                        order.order_status = OrderStatusEnum.CONFIRMED

                    self._send_payment_confirmation_email(
                        order.customer_id, order.order_code, float(order.total_amount)
                    )

            return {
                "success": True,
                "message": "Webhook processed",
                "order_id": order_id,
                "order_code": order.order_code
            }

        except InsufficientStockException as e:
            logger.error(f"Payment successful but insufficient stock: {str(e)}")
            return {
                "success": False,
                "error": f"Payment successful but insufficient stock: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_order_id_from_webhook(self, gateway: str, data: dict, verification: dict) -> Optional[int]:
        """Extract order ID from webhook data"""
        order_id = verification.get("order_id")
        if order_id:
            return int(order_id)

        try:
            if gateway == "momo":
                extra_data = data.get("extraData", "")
                if "order_id:" in extra_data:
                    return int(extra_data.split("order_id:")[1].split(";")[0])

            elif gateway == "vnpay":
                order_info = data.get("vnp_OrderInfo", "")
                if "OrderID:" in order_info:
                    return int(order_info.split("OrderID:")[1].split()[0])

            return None
        except (ValueError, IndexError):
            return None

    # ==================== EMAIL METHODS ====================

    def _send_order_confirmation_email(self, customer_id: int, order_code: str, total_amount: float) -> None:
        """Send order confirmation email"""
        try:
            customer = self.db.query(Customer).get(customer_id)
            if customer and customer.user:
                EmailService.send_order_confirmation_email(
                    customer.user.email,
                    customer.user.fullname or "Customer",
                    order_code,
                    total_amount
                )
        except Exception as e:
            logger.error(f"Failed to send order confirmation email: {str(e)}")

    def _send_payment_confirmation_email(self, customer_id: int, order_code: str, total_amount: float) -> None:
        """Send payment confirmation email"""
        try:
            customer = self.db.query(Customer).get(customer_id)
            if customer and customer.user:
                EmailService.send_payment_confirmation_email(
                    customer.user.email,
                    customer.user.fullname or "Customer",
                    order_code,
                    total_amount
                )
        except Exception as e:
            logger.error(f"Failed to send payment confirmation email: {str(e)}")

    def admin_confirm_order(self, order_id: int) -> Order:
        """Admin confirm pending order"""
        return self._update_order_status_simple(order_id,
                                                OrderStatusEnum.PENDING,
                                                OrderStatusEnum.CONFIRMED)

    def admin_process_order(self, order_id: int) -> Order:
        """Admin process confirmed order"""
        return self._update_order_status_simple(order_id,
                                                OrderStatusEnum.CONFIRMED,
                                                OrderStatusEnum.PROCESSING)

    def ship_order(self, order_id: int) -> Order:
        """Admin ship order"""
        return self._update_order_status_simple(order_id,
                                                OrderStatusEnum.PROCESSING,
                                                OrderStatusEnum.SHIPPED)

    def deliver_order(self, order_id: int) -> Order:
        """Admin deliver order"""
        with self.transaction():
            order = self._get_order(order_id)

            if order.order_status != OrderStatusEnum.SHIPPED:
                raise BadRequestException("Only shipped orders can be delivered")

            order.order_status = OrderStatusEnum.DELIVERED

            self._handle_cod_payment_and_email(order, OrderStatusEnum.DELIVERED)

        return order

    def _update_order_status_simple(self, order_id: int, required_status: OrderStatusEnum,
                                    new_status: OrderStatusEnum) -> Order:
        """Helper for simple status updates"""
        with self.transaction():
            order = self._get_order(order_id)

            if order.order_status != required_status:
                raise BadRequestException(f"Only {required_status.value} orders can be updated")

            order.order_status = new_status

        return order

    def approve_order_return(self, order_id: int, approved: bool, note: Optional[str] = None) -> Order:
        """Approve/reject order return"""
        with self.transaction():
            order = self._get_order(order_id)

            if order.order_status != OrderStatusEnum.RETURN_REQUESTED:
                raise BadRequestException("No return request found")

            if approved:
                self._restore_stock_for_items(order.order_items)

                if order.payment_status == PaymentStatusEnum.PAID:
                    self._process_refund_for_return(order, note)

                order.order_status = OrderStatusEnum.RETURNED
                order.payment_status = PaymentStatusEnum.REFUNDED
            else:
                order.order_status = OrderStatusEnum.DELIVERED

        return order

    def _process_refund_for_return(self, order: Order, note: str) -> None:
        """Process refund for returned order"""
        if order.payment_method in [PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY]:
            refund_result = self.payment_service.process_refund(
                order_id=order.id,
                amount=order.total_amount,
                reason=f"Order return: {note or 'No note'}"
            )

            if not refund_result.get("success"):
                raise BadRequestException(f"Refund failed: {refund_result.get('error')}")

    # ==================== AUTO-CANCELLATION ====================

    def auto_cancel_unpaid_orders(self) -> dict:
        """Auto-cancel unpaid orders after 24h"""
        logger.info("Checking for unpaid orders to auto-cancel")

        cutoff_time = datetime.now() - timedelta(hours=24)
        cancelled_count = 0

        with self.transaction():
            unpaid_orders = self.db.query(Order).filter(
                Order.order_status == OrderStatusEnum.PENDING,
                Order.payment_method.in_([PaymentMethodEnum.MOMO, PaymentMethodEnum.VNPAY]),
                Order.created_at < cutoff_time
            ).all()

            for order in unpaid_orders:
                order.order_status = OrderStatusEnum.CANCELLED
                order.payment_status = PaymentStatusEnum.CANCELLED
                order.cancellation_reason = "Auto-cancelled: Payment not completed within 24h"
                cancelled_count += 1

        return {
            "cancelled_count": cancelled_count,
            "processed_at": datetime.now().isoformat()
        }

    # ==================== REPORTS & STATISTICS ====================

    def get_order_statistics(self) -> dict:
        """Get order statistics"""
        return {
            "total_orders": self._count_total_orders(),
            "orders_by_status": self._count_orders_by_status(),
            "orders_by_payment": self._count_orders_by_payment(),
            "total_revenue": self._calculate_total_revenue(),
            "today_orders": self._count_today_orders(),
            "this_month_orders": self._count_month_orders()
        }

    def _count_total_orders(self) -> int:
        return self.db.query(func.count(Order.id)).scalar() or 0

    def _count_orders_by_status(self) -> Dict[str, int]:
        """Optimized version with single query"""
        results = self.db.query(
            Order.order_status,
            func.count(Order.id)
        ).group_by(Order.order_status).all()

        result_dict = {str(status): 0 for status in OrderStatusEnum}
        result_dict.update({str(status): count for status, count in results})
        return result_dict

    def _count_orders_by_payment(self) -> Dict[str, int]:
        """Optimized version with single query"""
        results = self.db.query(
            Order.payment_status,
            func.count(Order.id)
        ).group_by(Order.payment_status).all()

        result_dict = {str(status): 0 for status in PaymentStatusEnum}
        result_dict.update({str(status): count for status, count in results})
        return result_dict

    def _calculate_total_revenue(self) -> float:
        total = self.db.query(func.sum(Order.total_amount)).filter_by(
            payment_status=PaymentStatusEnum.PAID
        ).scalar() or Decimal('0')
        return float(total)

    def _count_today_orders(self) -> int:
        today = date.today()
        return self.db.query(func.count(Order.id)).filter(
            func.date(Order.created_at) == today
        ).scalar() or 0

    def _count_month_orders(self) -> int:
        today = date.today()
        first_day = datetime(today.year, today.month, 1)
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)

        return self.db.query(func.count(Order.id)).filter(
            Order.created_at >= first_day,
            Order.created_at < next_month
        ).scalar() or 0

    def get_revenue_report(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
        """Get revenue report"""
        query = self.db.query(Order).filter_by(payment_status=PaymentStatusEnum.PAID)

        if start_date:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Order.created_at >= start_datetime)

        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Order.created_at <= end_datetime)

        orders = query.all()

        if not orders:
            return {
                "total_revenue": 0,
                "number_of_orders": 0,
                "average_order_value": 0,
                "revenue_by_date": {},
                "revenue_by_method": {}
            }

        total_revenue = sum(order.total_amount for order in orders)
        revenue_by_date = {}
        revenue_by_method = {}

        for order in orders:
            date_key = order.created_at.strftime("%Y-%m-%d")
            revenue_by_date[date_key] = revenue_by_date.get(date_key, Decimal('0')) + order.total_amount

            method = order.payment_method.value
            revenue_by_method[method] = revenue_by_method.get(method, Decimal('0')) + order.total_amount

        return {
            "total_revenue": float(total_revenue),
            "number_of_orders": len(orders),
            "average_order_value": float(total_revenue / len(orders)),
            "revenue_by_date": {k: float(v) for k, v in revenue_by_date.items()},
            "revenue_by_method": {k: float(v) for k, v in revenue_by_method.items()}
        }

    def get_best_selling_products(self, limit: int = 10, start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> List[dict]:
        """Get best selling products"""
        query = self.db.query(
            OrderItem.product_id,
            Product.name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.subtotal).label('total_revenue')
        ).join(Product).join(Order).filter(
            Order.order_status == OrderStatusEnum.DELIVERED
        )

        if start_date:
            query = query.filter(Order.created_at >= datetime.strptime(start_date, "%Y-%m-%d"))

        if end_date:
            query = query.filter(Order.created_at <= datetime.strptime(end_date, "%Y-%m-%d"))

        results = query.group_by(OrderItem.product_id, Product.name) \
            .order_by(func.sum(OrderItem.quantity).desc()) \
            .limit(limit).all()

        return [
            {
                "product_id": r.product_id,
                "product_name": r.name,
                "total_quantity": r.total_quantity or 0,
                "total_revenue": float(r.total_revenue) if r.total_revenue else 0
            }
            for r in results
        ]

    def delete_order(self, order_id: int) -> dict:
        """Delete order (admin only)"""
        with self.transaction():
            order = self._get_order(order_id)

            if (order.order_status not in [OrderStatusEnum.CANCELLED, OrderStatusEnum.RETURNED] and
                    order.payment_status == PaymentStatusEnum.PAID):
                self._restore_stock_for_items(order.order_items)

            self.db.delete(order)

        return {"message": "Order deleted"}

    def buy_now(self, customer_id: int, product_id: int, quantity: int,
                shipping_info: dict, color_id: Optional[int] = None,
                size_id: Optional[int] = None) -> dict:
        """Mua ngay 1 sản phẩm - FIXED (không duplicate stock check)"""
        try:
            # Chỉ validate variant tồn tại, KHÔNG check stock ở đây
            product_detail = self._get_product_detail(product_id, color_id, size_id)
            if not product_detail:
                raise NotFoundException(f"Product variant not found")

            if product_detail.price is None:
                raise ValueError(f"Variant {product_detail.id} không có giá")

            product = self.db.query(Product).get(product_id)
            if not product:
                raise NotFoundException(f"Product {product_id} not found")

            product_price = Decimal(str(product_detail.price))
            total_amount = product_price * Decimal(str(quantity))
            shipping_fee = Decimal(str(shipping_info.get("shipping_fee", 0)))
            final_amount = total_amount + shipping_fee

            item = OrderItemRequest(
                product_id=product_id,
                quantity=quantity,
                color_id=color_id,
                size_id=size_id,
                price=product_price
            )

            order_request = CreateOrderRequest(
                items=[item],
                shipping_address=shipping_info.get("shipping_address"),
                shipping_phone=shipping_info.get("shipping_phone"),
                payment_method=PaymentMethodEnum(shipping_info.get("payment_method")),
                shipping_fee=shipping_fee,
                customer_note=shipping_info.get("customer_note", "Mua ngay"),
                total_amount=total_amount,
                final_amount=final_amount
            )

            # Stock sẽ được kiểm tra trong create_order() -> check_stock_availability()
            return self.create_order(customer_id, order_request)

        except Exception as e:
            logger.error(f"Buy now failed for customer {customer_id}: {str(e)}")
            raise