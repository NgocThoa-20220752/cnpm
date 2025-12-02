from sqlalchemy.orm import Session
from typing import Optional

from sqlalchemy import func
from app.enum import ProductStatusEnum
from app.models.product import Product, ProductDetail, ProductImage, ProductColor, ProductSize, PackagingType
from app.schemas.request.product_req import (
    CreateProductRequest, UpdateProductRequest,
    CreateProductDetailRequest, UpdateProductDetailRequest,
    CreateProductImageRequest, CreateProductColorRequest,
    CreateProductSizeRequest, CreatePackagingTypeRequest
)
from app.exceptions import NotFoundException, ConflictException
from app.functions.file_utils import FileUtils

from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    @contextmanager
    def transaction(self):
        """Transaction context manager - THÊM expire_all"""
        try:
            logger.debug("🔄 Starting transaction")
            yield self.db
            self.db.commit()
            logger.debug("✅ Transaction committed")
            self.db.expire_all()
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Transaction failed, rolled back: {str(e)}")
            raise

    # ==================== PRODUCT CRUD ====================

    def get_products(self, page: int = 1, limit: int = 20, search: Optional[str] = None,
                     category_id: Optional[int] = None):
        """Get products with pagination and filters"""
        query = self.db.query(Product)

        if search:
            query = query.filter(
                (Product.name.ilike(f"%{search}%")) |
                (Product.slug.ilike(f"%{search}%"))
            )

        if category_id:
            query = query.filter_by(category_id= category_id)

        total = query.count()
        products = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": products
        }

    def get_product_by_id(self, product_id: int):
        """Get product by ID"""
        product = self.db.query(Product).filter_by(id= product_id).first()
        if not product:
            raise NotFoundException("Product not found")
        return product

    def get_product_by_slug(self, slug: str):
        """Get product by slug"""
        product = self.db.query(Product).filter_by(slug= slug).first()
        if not product:
            raise NotFoundException("Product not found")
        return product

    def create_product(self, request: CreateProductRequest):
        """Create new product"""
        # Check if slug exists
        existing = self.db.query(Product).filter_by(slug= request.slug).first()
        if existing:
            raise ConflictException("Slug already exists")

        product = Product(
            name=request.name,
            slug=request.slug,
            category_id=request.category_id,
            price=request.price
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, product_id: int, request: UpdateProductRequest):
        """Update product"""
        product = self.get_product_by_id(product_id)

        if request.name is not None:
            product.name = request.name
        if request.slug is not None:
            # Check if new slug exists
            existing = self.db.query(Product).filter_by(
                slug= request.slug).filter(
                Product.id != product_id
            ).first()
            if existing:
                raise ConflictException("Slug already exists")
            product.slug = request.slug
        if request.category_id is not None:
            product.category_id = request.category_id
        if request.price is not None:
            product.price = request.price

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product_id: int):
        """Delete product"""
        product = self.get_product_by_id(product_id)
        self.db.delete(product)
        self.db.commit()
        return {"message": "Product deleted successfully"}

    # ==================== PRODUCT DETAIL CRUD ====================

    def create_product_detail(self, request: CreateProductDetailRequest):
        """Create product detail - FIXED NULL handling"""
        with self.transaction():
            # Validate product exists
            product = self.get_product_by_id(request.product_id)

            # Validate foreign keys nếu được cung cấp
            if request.color_id:
                color = self.db.query(ProductColor).filter_by(id=request.color_id).first()
                if not color:
                    raise NotFoundException(f"Color with ID {request.color_id} not found")

            if request.size_id:
                size = self.db.query(ProductSize).filter_by(id=request.size_id).first()
                if not size:
                    raise NotFoundException(f"Size with ID {request.size_id} not found")

            if request.packaging_type_id:
                packaging = self.db.query(PackagingType).filter_by(id=request.packaging_type_id).first()
                if not packaging:
                    raise NotFoundException(f"Packaging type with ID {request.packaging_type_id} not found")

            filters = [ProductDetail.product_id == request.product_id]

            # Xử lý color_id
            if request.color_id:
                filters.append(ProductDetail.color_id == request.color_id)
            else:
                filters.append(ProductDetail.color_id.is_(None))

            # Xử lý size_id
            if request.size_id:
                filters.append(ProductDetail.size_id == request.size_id)
            else:
                filters.append(ProductDetail.size_id.is_(None))

            # Xử lý packaging_type_id
            if request.packaging_type_id:
                filters.append(ProductDetail.packaging_type_id == request.packaging_type_id)
            else:
                filters.append(ProductDetail.packaging_type_id.is_(None))

            # Check if combination already exists
            existing = self.db.query(ProductDetail).filter(*filters).first()

            if existing:
                raise ConflictException("Product variant with this combination already exists")

            # Create detail
            detail = ProductDetail(
                product_id=request.product_id,
                packaging_type_id=request.packaging_type_id,
                color_id=request.color_id,
                size_id=request.size_id,
                description=request.description,
                ingredients=request.ingredients,
                usage=request.usage,
                benefits=request.benefits,
                storage=request.storage,
                stock=request.stock,
                sku=request.sku
            )
            self.db.add(detail)
            self.db.flush()

            # Tự động cập nhật trạng thái sản phẩm sau khi thêm biến thể
            self.auto_update_product_status(request.product_id)

        return detail

    def update_product_detail(self, detail_id: int, request: UpdateProductDetailRequest):
        """Update product detail - FIXED any() logic"""
        with self.transaction():
            detail = self.db.query(ProductDetail).filter_by(id=detail_id).first()
            if not detail:
                raise NotFoundException("Product detail not found")

            # ✅ FIXED: Lưu giá trị mới để check duplicate
            new_color = request.color_id if request.color_id is not None else detail.color_id
            new_size = request.size_id if request.size_id is not None else detail.size_id
            new_packaging = request.packaging_type_id if request.packaging_type_id is not None else detail.packaging_type_id

            # Validate foreign keys nếu được cung cấp
            if request.color_id is not None:
                color = self.db.query(ProductColor).filter_by(id=request.color_id).first()
                if not color:
                    raise NotFoundException(f"Color with ID {request.color_id} not found")
                detail.color_id = request.color_id

            if request.size_id is not None:
                size = self.db.query(ProductSize).filter_by(id=request.size_id).first()
                if not size:
                    raise NotFoundException(f"Size with ID {request.size_id} not found")
                detail.size_id = request.size_id

            if request.packaging_type_id is not None:
                packaging = self.db.query(PackagingType).filter_by(id=request.packaging_type_id).first()
                if not packaging:
                    raise NotFoundException(f"Packaging type with ID {request.packaging_type_id} not found")
                detail.packaging_type_id = request.packaging_type_id

            # Update other fields
            if request.description is not None:
                detail.description = request.description
            if request.ingredients is not None:
                detail.ingredients = request.ingredients
            if request.usage is not None:
                detail.usage = request.usage
            if request.benefits is not None:
                detail.benefits = request.benefits
            if request.storage is not None:
                detail.storage = request.storage
            if request.stock is not None:
                detail.stock = request.stock
            if request.sku is not None:
                detail.sku = request.sku

            # ✅ FIXED: Luôn check duplicate sau update, không cần any()
            filters = [
                ProductDetail.product_id == detail.product_id,
                ProductDetail.id != detail_id
            ]

            # Xử lý NULL đúng cách
            if new_color:
                filters.append(ProductDetail.color_id == new_color)
            else:
                filters.append(ProductDetail.color_id.is_(None))

            if new_size:
                filters.append(ProductDetail.size_id == new_size)
            else:
                filters.append(ProductDetail.size_id.is_(None))

            if new_packaging:
                filters.append(ProductDetail.packaging_type_id == new_packaging)
            else:
                filters.append(ProductDetail.packaging_type_id.is_(None))

            existing = self.db.query(ProductDetail).filter(*filters).first()

            if existing:
                raise ConflictException("Another product variant with this combination already exists")

            self.db.flush()

            # Tự động cập nhật trạng thái sản phẩm sau khi sửa biến thể
            self.auto_update_product_status(detail.product_id)

        return detail

    def delete_product_detail(self, detail_id: int):
        """Delete product detail với transaction - FIXED"""
        with self.transaction():
            detail = self.db.query(ProductDetail).filter_by(id=detail_id).first()
            if not detail:
                raise NotFoundException("Product detail not found")

            product_id = detail.product_id
            self.db.delete(detail)
            self.db.flush()

            # Tự động cập nhật trạng thái sản phẩm sau khi xóa biến thể
            self.auto_update_product_status(product_id)

        return {"message": "Product detail deleted successfully"}

    # ==================== PRODUCT IMAGE CRUD ====================

    def create_product_image(self, request: CreateProductImageRequest):
        """Create product image - THÊM logic main image"""
        if request.is_main:
            self.db.query(ProductImage).filter_by(
                product_id=request.product_id,
                is_main=True
            ).update({"is_main": False})

        image = ProductImage(
            product_id=request.product_id,
            product_detail_id=request.product_detail_id,
            image_url=request.image_url,
            is_main=request.is_main,
            display_order=request.display_order
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def delete_product_image(self, image_id: int):
        """Delete product image - THÊM logic main image"""
        image = self.db.query(ProductImage).filter_by(id=image_id).first()
        if not image:
            raise NotFoundException("Image not found")

        # Delete physical file
        FileUtils.delete_file(image.image_url)
        if image.is_main:
            other_image = self.db.query(ProductImage).filter(
                ProductImage.product_id == image.product_id,
                ProductImage.id != image_id
            ).first()
            if other_image:
                other_image.is_main = True

        self.db.delete(image)
        self.db.commit()
        return {"message": "Image deleted successfully"}

    def get_product_images(self, product_id: int):
        """Get all images of a product"""
        images = self.db.query(ProductImage).filter_by(
            product_id= product_id
        ).order_by(ProductImage.display_order).all()
        return images

    # ==================== PRODUCT COLOR CRUD ====================

    def get_all_colors(self):
        """Get all colors"""
        return self.db.query(ProductColor).all()

    def create_product_color(self, request: CreateProductColorRequest):
        """Create product color"""
        color = ProductColor(
            name=request.name,
            code=request.code
        )
        self.db.add(color)
        self.db.commit()
        self.db.refresh(color)
        return color

    def update_product_color(self, color_id: int, request: CreateProductColorRequest):
        """Update product color - ĐÃ XÓA STOCK"""
        color = self.db.query(ProductColor).filter_by(id=color_id).first()
        if not color:
            raise NotFoundException("Color not found")

        if request.name != color.name:
            existing = self.db.query(ProductColor).filter_by(name=request.name).first()
            if existing:
                raise ConflictException("Color name already exists")

        if request.code != color.code:
            existing = self.db.query(ProductColor).filter_by(code=request.code).first()
            if existing:
                raise ConflictException("Color code already exists")
        color.name = request.name
        color.code = request.code

    def delete_product_color(self, color_id: int):
        """Delete product color - THÊM check đang dùng"""
        # ✅ THÊM: Check if color is being used in any product detail
        usage = self.db.query(ProductDetail).filter_by(color_id=color_id).first()
        if usage:
            raise ConflictException("Cannot delete color that is being used in products")

        color = self.db.query(ProductColor).filter_by(id=color_id).first()
        if not color:
            raise NotFoundException("Color not found")
        self.db.delete(color)
        self.db.commit()
        return {"message": "Color deleted successfully"}

    # ==================== PRODUCT SIZE CRUD ====================

    def get_all_sizes(self):
        """Get all sizes"""
        return self.db.query(ProductSize).all()

    def create_product_size(self, request: CreateProductSizeRequest):
        """Create product size"""
        size = ProductSize(name=request.name)
        self.db.add(size)
        self.db.commit()
        self.db.refresh(size)
        return size

    def update_product_size(self, size_id: int, request: CreateProductSizeRequest):
        """Update product size"""
        size = self.db.query(ProductSize).filter_by(id= size_id).first()
        if not size:
            raise NotFoundException("Size not found")

        size.name = request.name
        self.db.commit()
        self.db.refresh(size)
        return size

    def delete_product_size(self, size_id: int):
        """Delete product size - THÊM check đang dùng"""
        usage = self.db.query(ProductDetail).filter_by(size_id=size_id).first()
        if usage:
            raise ConflictException("Cannot delete size that is being used in products")

        size = self.db.query(ProductSize).filter_by(id=size_id).first()
        if not size:
            raise NotFoundException("Size not found")
        self.db.delete(size)
        self.db.commit()
        return {"message": "Size deleted successfully"}

    # ==================== PACKAGING TYPE CRUD ====================

    def get_all_packaging_types(self):
        """Get all packaging types"""
        return self.db.query(PackagingType).all()

    def create_packaging_type(self, request: CreatePackagingTypeRequest):
        """Create packaging type"""
        packaging = PackagingType(name=request.name)
        self.db.add(packaging)
        self.db.commit()
        self.db.refresh(packaging)
        return packaging

    def update_packaging_type(self, packaging_id: int, request: CreatePackagingTypeRequest):
        """Update packaging type"""
        packaging = self.db.query(PackagingType).filter_by(id= packaging_id).first()
        if not packaging:
            raise NotFoundException("Packaging type not found")

        packaging.name = request.name
        self.db.commit()
        self.db.refresh(packaging)
        return packaging

    def delete_packaging_type(self, packaging_id: int):
        """Delete packaging type - THÊM check đang dùng"""
        usage = self.db.query(ProductDetail).filter_by(packaging_type_id=packaging_id).first()
        if usage:
            raise ConflictException("Cannot delete packaging type that is being used in products")

        packaging = self.db.query(PackagingType).filter_by(id=packaging_id).first()
        if not packaging:
            raise NotFoundException("Packaging type not found")
        self.db.delete(packaging)
        self.db.commit()
        return {"message": "Packaging type deleted successfully"}

    # ==================== LOW STOCK PRODUCTS ====================

    def get_low_stock_products(self, threshold: int = 10):
        """Get product details with low stock (dựa trên ProductDetail)"""
        details = self.db.query(ProductDetail).filter(
            ProductDetail.stock <= threshold
        ).all()

        result = []
        for detail in details:
            product = self.get_product_by_id(detail.product_id)
            color = self.db.query(ProductColor).filter_by(id=detail.color_id).first() if detail.color_id else None
            size = self.db.query(ProductSize).filter_by(id=detail.size_id).first() if detail.size_id else None

            result.append({
                "product_id": product.id,
                "product_name": product.name,
                "detail_id": detail.id,
                "color_id": color.id if color else None,
                "color_name": color.name if color else None,
                "size_id": size.id if size else None,
                "size_name": size.name if size else None,
                "stock": detail.stock,
                "threshold": threshold,
                "sku": detail.sku
            })

        return result

    def update_product_status(self, product_id: int, status: ProductStatusEnum):
        """Update product status"""
        product = self.get_product_by_id(product_id)
        product.status = status
        self.db.commit()
        self.db.refresh(product)
        return product

    def auto_update_product_status(self, product_id: int):
        """Tự động cập nhật trạng thái sản phẩm dựa trên tồn kho"""
        product = self.get_product_by_id(product_id)

        total_stock = self.db.query(func.sum(ProductDetail.stock)) \
                          .filter_by(product_id=product_id) \
                          .scalar() or 0

        old_status = product.status

        if total_stock <= 0 and product.status == ProductStatusEnum.ACTIVE:
            product.status = ProductStatusEnum.HIDDEN
        elif total_stock > 0 and product.status == ProductStatusEnum.HIDDEN:
            product.status = ProductStatusEnum.ACTIVE

        if old_status != product.status:
            self.db.commit()

        return product

    def get_active_products(self, page: int = 1, limit: int = 20, search: Optional[str] = None,
                            category_id: Optional[int] = None):
        """Chỉ lấy sản phẩm đang active (cho khách hàng)"""
        query = self.db.query(Product).filter_by(status=ProductStatusEnum.ACTIVE)

        if search:
            query = query.filter(
                (Product.name.ilike(f"%{search}%")) |
                (Product.slug.ilike(f"%{search}%"))
            )

        if category_id:
            query = query.filter_by(category_id=category_id)

        total = query.count()
        products = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": products
        }