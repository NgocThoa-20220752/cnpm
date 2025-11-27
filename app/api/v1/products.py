from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional


from app.Dependencies import get_admin_or_employee
from app.core.database import get_db
from app.functions.file_utils import FileUtils
from app.schemas.request.product_req import (
    CreateProductRequest, UpdateProductRequest,
    CreateProductDetailRequest, UpdateProductDetailRequest,
    CreateProductImageRequest, CreateProductColorRequest,
    CreateProductSizeRequest, CreatePackagingTypeRequest
)
from app.schemas.response.product_resp import (
    ProductResponse, ProductListResponse, ProductDetailResponse,
    ProductImageResponse, ProductColorResponse, ProductSizeResponse,
    PackagingTypeResponse, LowStockProductResponse
)
from app.services.product_service import ProductService
from app.models.user import User


router = APIRouter(prefix="/products", tags=["products"])


# ==================== PRODUCT ENDPOINTS ====================

@router.get("", response_model=ProductListResponse)
async def get_products(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    """Get products with pagination and filters"""
    service = ProductService(db)
    return service.get_products(page, limit, search, category_id)


@router.get("/search", response_model=ProductListResponse)
async def search_products(
        q: str = Query(..., min_length=1),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db)
):
    """Search products by name or slug"""
    service = ProductService(db)
    return service.get_products(page=page, limit=limit, search=q)


@router.get("/low-stock", response_model=List[LowStockProductResponse])
async def get_low_stock_products(
        threshold: int = Query(10, ge=0),
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Get products with low stock (Admin/Employee only)"""
    service = ProductService(db)
    return service.get_low_stock_products(threshold)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: int,
        db: Session = Depends(get_db)
):
    """Get product by ID"""
    service = ProductService(db)
    return service.get_product_by_id(product_id)


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
        slug: str,
        db: Session = Depends(get_db)
):
    """Get product by slug"""
    service = ProductService(db)
    return service.get_product_by_slug(slug)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
        request: CreateProductRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Create product (Admin/Employee only)"""
    service = ProductService(db)
    return service.create_product(request)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
        product_id: int,
        request: UpdateProductRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update product (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_product(product_id, request)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
        product_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete product (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_product(product_id)
    return None


# ==================== PRODUCT DETAILS ====================

@router.post("/{product_id}/details", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product_detail(
        product_id: int,
        request: CreateProductDetailRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Create product detail (Admin/Employee only)"""
    # Ensure product exists and set product_id
    service = ProductService(db)
    service.get_product_by_id(product_id)

    detail_data = request.model_dump()
    detail_data['product_id'] = product_id
    detail_request = CreateProductDetailRequest(**detail_data)

    return service.create_product_detail(detail_request)


@router.put("/details/{detail_id}", response_model=ProductDetailResponse)
async def update_product_detail(
        detail_id: int,
        request: UpdateProductDetailRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update product detail (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_product_detail(detail_id, request)


@router.delete("/details/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_detail(
        detail_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete product detail (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_product_detail(detail_id)
    return None


# ==================== PRODUCT IMAGES ====================

@router.post("/{product_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
        product_id: int,
        file: UploadFile = File(...),
        is_main: bool = False,
        display_order: int = 0,
        product_detail_id: Optional[int] = None,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Upload product image (Admin/Employee only)"""
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Upload file
    file_path = await FileUtils.save_upload_file(file, "products")

    # Create image record
    service = ProductService(db)
    request = CreateProductImageRequest(
        product_id=product_id,
        product_detail_id=product_detail_id,
        image_url=file_path,
        is_main=is_main,
        display_order=display_order
    )

    return service.create_product_image(request)


@router.get("/{product_id}/images", response_model=List[ProductImageResponse])
async def get_product_images(
        product_id: int,
        db: Session = Depends(get_db)
):
    """Get product images"""
    service = ProductService(db)
    return service.get_product_images(product_id)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(
        image_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete product image (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_product_image(image_id)
    return None


# ==================== COLORS ====================

@router.get("/colors/all", response_model=List[ProductColorResponse])
async def get_colors(db: Session = Depends(get_db)):
    """Get all colors"""
    service = ProductService(db)
    return service.get_all_colors()


@router.post("/colors", response_model=ProductColorResponse, status_code=status.HTTP_201_CREATED)
async def create_color(
        request: CreateProductColorRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Create color (Admin/Employee only)"""
    service = ProductService(db)
    return service.create_product_color(request)


@router.put("/colors/{color_id}", response_model=ProductColorResponse)
async def update_color(
        color_id: int,
        request: CreateProductColorRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update color (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_product_color(color_id, request)


@router.patch("/colors/{color_id}/stock", response_model=ProductColorResponse)
async def update_color_stock(
        color_id: int,
        stock: int = Query(..., ge=0),
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update color stock (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_product_color_stock(color_id, stock)


@router.delete("/colors/{color_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_color(
        color_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete color (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_product_color(color_id)
    return None


# ==================== SIZES ====================

@router.get("/sizes/all", response_model=List[ProductSizeResponse])
async def get_sizes(db: Session = Depends(get_db)):
    """Get all sizes"""
    service = ProductService(db)
    return service.get_all_sizes()


@router.post("/sizes", response_model=ProductSizeResponse, status_code=status.HTTP_201_CREATED)
async def create_size(
        request: CreateProductSizeRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Create size (Admin/Employee only)"""
    service = ProductService(db)
    return service.create_product_size(request)


@router.put("/sizes/{size_id}", response_model=ProductSizeResponse)
async def update_size(
        size_id: int,
        request: CreateProductSizeRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update size (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_product_size(size_id, request)


@router.delete("/sizes/{size_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_size(
        size_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete size (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_product_size(size_id)
    return None


# ==================== PACKAGING TYPES ====================

@router.get("/packaging/all", response_model=List[PackagingTypeResponse])
async def get_packaging_types(db: Session = Depends(get_db)):
    """Get all packaging types"""
    service = ProductService(db)
    return service.get_all_packaging_types()


@router.post("/packaging", response_model=PackagingTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_packaging_type(
        request: CreatePackagingTypeRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Create packaging type (Admin/Employee only)"""
    service = ProductService(db)
    return service.create_packaging_type(request)


@router.put("/packaging/{packaging_id}", response_model=PackagingTypeResponse)
async def update_packaging_type(
        packaging_id: int,
        request: CreatePackagingTypeRequest,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Update packaging type (Admin/Employee only)"""
    service = ProductService(db)
    return service.update_packaging_type(packaging_id, request)


@router.delete("/packaging/{packaging_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_packaging_type(
        packaging_id: int,
        _current_user: User = Depends(get_admin_or_employee),
        db: Session = Depends(get_db)
):
    """Delete packaging type (Admin/Employee only)"""
    service = ProductService(db)
    service.delete_packaging_type(packaging_id)
    return None