from sqlalchemy import Column, Integer, String, Text, DECIMAL, ForeignKey, Boolean, JSON, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.enum import ProductStatusEnum
from app.models.base import BaseModel


class Category(BaseModel):
    """Category model"""
    __tablename__ = "categories"

    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    # Relationships
    parent = relationship("Category", remote_side="Category.id", backref="children")
    products = relationship("Product", back_populates="category")


class Product(BaseModel):
    """Product model"""
    __tablename__ = "products"

    name = Column(String(200), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    price = Column(DECIMAL(12, 2), nullable=False)
    # Thêm trạng thái sản phẩm
    status = Column(SQLEnum(ProductStatusEnum), default=ProductStatusEnum.ACTIVE, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="products")
    product_details = relationship("ProductDetail", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")


class ProductDetail(BaseModel):
    """Product detail model"""
    __tablename__ = "product_details"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    packaging_type_id = Column(Integer, ForeignKey("packaging_types.id", ondelete="SET NULL"), nullable=True)
    color_id = Column(Integer, ForeignKey("product_colors.id", ondelete="SET NULL"), nullable=True)
    size_id = Column(Integer, ForeignKey("product_sizes.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=True)
    usage = Column(JSON, nullable=True)
    benefits = Column(JSON, nullable=True)
    storage = Column(Text, nullable=True)
    # THÊM SỐ LƯỢNG VÀO BẢNG CHI TIẾT SẢN PHẨM
    stock = Column(Integer, default=0)
    # Thêm SKU để dễ quản lý
    sku = Column(String(100), unique=True, index=True)

    # Relationships
    product = relationship("Product", back_populates="product_details")
    packaging_type = relationship("PackagingType", back_populates="product_details")
    color = relationship("ProductColor", back_populates="product_details")
    size = relationship("ProductSize", back_populates="product_details")


class ProductImage(BaseModel):
    """Product image model"""
    __tablename__ = "product_images"

    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_detail_id = Column(Integer, ForeignKey("product_details.id", ondelete="CASCADE"), nullable=True)
    image_url = Column(String(255), nullable=False)
    is_main = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)

    # Relationships
    product = relationship("Product", back_populates="images")
    product_detail = relationship("ProductDetail")


class ProductColor(BaseModel):
    """Product color model"""
    __tablename__ = "product_colors"

    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)

    # Relationships
    product_details = relationship("ProductDetail", back_populates="color")


class ProductSize(BaseModel):
    """Product size model"""
    __tablename__ = "product_sizes"

    name = Column(String(20), nullable=False)

    # Relationships
    product_details = relationship("ProductDetail", back_populates="size")


class PackagingType(BaseModel):
    """Packaging type model"""
    __tablename__ = "packaging_types"

    name = Column(String(20), nullable=False)

    # Relationships
    product_details = relationship("ProductDetail", back_populates="packaging_type")