from sqlalchemy.orm import Session
from typing import Optional
from app.models.product import Product, ProductDetail, ProductImage, ProductColor, ProductSize, PackagingType
from app.schemas.request.product_req import (
    CreateProductRequest, UpdateProductRequest,
    CreateProductDetailRequest, UpdateProductDetailRequest,
    CreateProductImageRequest, CreateProductColorRequest,
    CreateProductSizeRequest, CreatePackagingTypeRequest
)
from app.exceptions import NotFoundException, ConflictException
from app.functions.file_utils import FileUtils


class ProductService:
    def __init__(self, db: Session):
        self.db = db

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
        """Create product detail"""
        self.get_product_by_id(request.product_id)

        detail = ProductDetail(
            product_id=request.product_id,
            packaging_type_id=request.packaging_type_id,
            color_id=request.color_id,
            size_id=request.size_id,
            description=request.description,
            ingredients=request.ingredients,
            usage=request.usage,
            benefits=request.benefits,
            storage=request.storage
        )
        self.db.add(detail)
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def update_product_detail(self, detail_id: int, request: UpdateProductDetailRequest):
        """Update product detail"""
        detail = self.db.query(ProductDetail).filter_by(id= detail_id).first()
        if not detail:
            raise NotFoundException("Product detail not found")

        if request.packaging_type_id is not None:
            detail.packaging_type_id = request.packaging_type_id
        if request.color_id is not None:
            detail.color_id = request.color_id
        if request.size_id is not None:
            detail.size_id = request.size_id
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

        self.db.commit()
        self.db.refresh(detail)
        return detail

    def delete_product_detail(self, detail_id: int):
        """Delete product detail"""
        detail = self.db.query(ProductDetail).filter_by(id= detail_id).first()
        if not detail:
            raise NotFoundException("Product detail not found")
        self.db.delete(detail)
        self.db.commit()
        return {"message": "Product detail deleted successfully"}

    # ==================== PRODUCT IMAGE CRUD ====================

    def create_product_image(self, request: CreateProductImageRequest):
        """Create product image"""
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
        """Delete product image"""
        image = self.db.query(ProductImage).filter_by(id= image_id).first()
        if not image:
            raise NotFoundException("Image not found")

        # Delete physical file
        FileUtils.delete_file(image.image_url)

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
            code=request.code,
            stock=request.stock
        )
        self.db.add(color)
        self.db.commit()
        self.db.refresh(color)
        return color

    def update_product_color(self, color_id: int, request: CreateProductColorRequest):
        """Update product color"""
        color = self.db.query(ProductColor).filter_by(id= color_id).first()
        if not color:
            raise NotFoundException("Color not found")

        color.name = request.name
        color.code = request.code
        color.stock = request.stock

        self.db.commit()
        self.db.refresh(color)
        return color

    def update_product_color_stock(self, color_id: int, stock: int):
        """Update color stock"""
        color = self.db.query(ProductColor).filter_by(id= color_id).first()
        if not color:
            raise NotFoundException("Color not found")
        color.stock = stock
        self.db.commit()
        self.db.refresh(color)
        return color

    def delete_product_color(self, color_id: int):
        """Delete product color"""
        color = self.db.query(ProductColor).filter_by(id= color_id).first()
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
        """Delete product size"""
        size = self.db.query(ProductSize).filter_by(id= size_id).first()
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
        """Delete packaging type"""
        packaging = self.db.query(PackagingType).filter_by(id= packaging_id).first()
        if not packaging:
            raise NotFoundException("Packaging type not found")
        self.db.delete(packaging)
        self.db.commit()
        return {"message": "Packaging type deleted successfully"}

    # ==================== LOW STOCK PRODUCTS ====================

    def get_low_stock_products(self, threshold: int = 10):
        """Get products with low stock"""
        colors = self.db.query(ProductColor).filter(ProductColor.stock <= threshold).all()

        result = []
        for color in colors:
            # Get products using this color
            product_details = self.db.query(ProductDetail).filter_by(
                color_id= color.id
            ).all()

            products = []
            for detail in product_details:
                product = self.get_product_by_id(detail.product_id)
                products.append(product)

            result.append({
                "color_id": color.id,
                "color_name": color.name,
                "stock": color.stock,
                "products": products
            })

        return result