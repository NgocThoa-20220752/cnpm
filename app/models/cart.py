from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Cart(BaseModel):
    """Cart model"""
    __tablename__ = "carts"

    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Relationships
    customer = relationship("Customer", back_populates="carts")
    cart_items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(BaseModel):
    """Cart item model"""
    __tablename__ = "cart_items"

    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    color_id = Column(Integer, ForeignKey('product_colors.id'), nullable=True)
    size_id = Column(Integer, ForeignKey('product_sizes.id'), nullable=True)

    quantity = Column(Integer, default=1, nullable=False)

    # Relationships
    cart = relationship("Cart", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
    color = relationship("ProductColor")
    size = relationship("ProductSize")