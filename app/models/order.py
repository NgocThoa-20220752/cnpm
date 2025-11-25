from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, Enum as SQLEnum, Text
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

    # Thông tin giao hàng
    shipping_address = Column(Text, nullable=False)
    shipping_phone = Column(String(15), nullable=False)
    shipping_fee = Column(DECIMAL(10, 2), default=0, nullable=False)
    note = Column(Text, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipping_info = relationship("ShippingInfo", back_populates="order", cascade="all, delete-orphan", uselist=False)


class OrderItem(BaseModel):
    """Order item model"""
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_detail_id = Column(Integer, ForeignKey("product_details.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    product_name = Column(String(200), nullable=False)  # Tên sản phẩm tại thời điểm order

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    product_detail = relationship("ProductDetail")


class ShippingInfo(BaseModel):
    """Shipping information model"""
    __tablename__ = "shipping_info"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(50), nullable=False)
    district = Column(String(50), nullable=False)
    ward = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)

    # Relationship
    order = relationship("Order", back_populates="shipping_info", uselist=False)