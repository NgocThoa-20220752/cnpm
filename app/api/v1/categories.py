from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.schemas.request.category_req import CreateCategoryRequest, UpdateCategoryRequest
from app.schemas.response.category_resp import CategoryResponse, CategoryListResponse, CategoryWithChildrenResponse
from app.services.category_service import CategoryService
from app.Dependencies import get_admin_or_employee
from app.models.user import User

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get(
    "",
    response_model=CategoryListResponse,
    summary="Get all categories",
    description="Retrieve all categories with optional search filter"
)
async def get_categories(
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    category_service = CategoryService(db)
    return category_service.get_categories(search)

@router.get(
    "/tree",
    response_model=List[CategoryWithChildrenResponse],
    summary="Get category tree",
    description="Get category tree structure with parent-child relationships"
)
async def get_category_tree(db: Session = Depends(get_db)):
    category_service = CategoryService(db)
    return category_service.get_category_tree()

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category by ID",
    description="Retrieve a specific category by its ID"
)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category_service = CategoryService(db)
    category = category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category

@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new category (Admin/Employee only)"
)
async def create_category(
    request: CreateCategoryRequest,
    _current_user: User = Depends(get_admin_or_employee),
    db: Session = Depends(get_db)
):
    category_service = CategoryService(db)
    return category_service.create_category(request)

@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Update an existing category (Admin/Employee only)"
)
async def update_category(
    category_id: int,
    request: UpdateCategoryRequest,
    _current_user: User = Depends(get_admin_or_employee),
    db: Session = Depends(get_db)
):
    category_service = CategoryService(db)
    category = category_service.update_category(category_id, request)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category

@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    description="Delete a category (Admin/Employee only)"
)
async def delete_category(
    category_id: int,
    _current_user: User = Depends(get_admin_or_employee),
    db: Session = Depends(get_db)
):
    category_service = CategoryService(db)
    try:
        success = category_service.delete_category(category_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete category: {str(e)}"
        )