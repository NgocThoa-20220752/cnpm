from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, Enum as SQLEnum, Text, Numeric
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enum import PaymentMethodEnum, PaymentStatusEnum, OrderStatusEnum


class Order(BaseModel):
    """Order model"""
    __tablename__ = "orders"

    order_code = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    payment_method = Column(SQLEnum(PaymentMethodEnum), nullable=False)
    payment_status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING, nullable=False)
    order_status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.PENDING, nullable=False)

    # THÊM CÁC TRƯỜNG TỔNG TIỀN
    final_amount = Column(Numeric(10, 2), nullable=False)     # Tổng thanh toán

    # Thông tin giao hàng (giữ lại - người dùng nhập trực tiếp)
    shipping_address = Column(Text, nullable=False)
    shipping_phone = Column(String(15), nullable=False)
    shipping_fee = Column(DECIMAL(10, 2), default=0, nullable=False)
    note = Column(Text, nullable=True)

    # Relationships (giữ nguyên)
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    @property
    def customer_name(self):
        if self.customer and self.customer.user:
            return self.customer.user.full_name
        return "Khách hàng"  # Fallback value

    @property
    def customer_phone(self):
        if self.customer and self.customer.user:
            return self.customer.user.phone
        return "N/A"  # Fallback value


class OrderItem(BaseModel):
    """Order item model (chi tiết đơn hàng)"""
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_detail_id = Column(Integer, ForeignKey("product_details.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    product_name = Column(String(200), nullable=False)  # Tên sản phẩm tại thời điểm order

    # Relationships (giữ nguyên)
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    product_detail = relationship("ProductDetail")