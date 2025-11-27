from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, cast
from app.models.product import Category
from app.schemas.request.category_req import CreateCategoryRequest, UpdateCategoryRequest
from app.exceptions import NotFoundException, ConflictException


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_categories(self, search: Optional[str] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        query = self.db.query(Category)

        if search:
            query = query.filter(
                (Category.name.ilike(f"%{search}%")) |
                (Category.slug.ilike(f"%{search}%"))
            )

        total = query.count()

        # Thêm phân trang
        categories = query.order_by(Category.display_order) \
            .offset((page - 1) * limit) \
            .limit(limit) \
            .all()

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": categories
        }

    def get_category_by_id(self, category_id: int) -> Category:
        category = self.db.query(Category).filter_by(id= category_id).first()
        if not category:
            raise NotFoundException("Category not found")
        return cast(Category,category)

    def get_category_tree(self) -> List[Dict[str, Any]]:
        """Get category tree structure với performance tối ưu"""
        categories = self.db.query(Category).order_by(Category.display_order).all()

        # Group children by parent_id để tránh O(n²)
        children_by_parent: Dict[Optional[int], List[Any]] = {}
        for cat in categories:
            if cat.parent_id not in children_by_parent:
                children_by_parent[cat.parent_id] = []
            children_by_parent[cat.parent_id].append(cat)

        def build_tree(category: Any) -> Dict[str, Any]:
            """Helper function để build tree recursively"""
            children = children_by_parent.get(category.id, [])
            return {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "parent_id": category.parent_id,
                "description": category.description,
                "display_order": category.display_order,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "children": [build_tree(child) for child in children]
            }

        # Build tree từ root categories (parent_id is None)
        root_categories = [cat for cat in categories if cat.parent_id is None]
        return [build_tree(cat) for cat in root_categories]

    def create_category(self, request: CreateCategoryRequest) -> Category:
        try:
            # Check if slug exists
            existing = self.db.query(Category).filter_by(slug= request.slug).first()
            if existing:
                raise ConflictException("Slug already exists")

            # Check if parent_id exists (nếu có)
            if request.parent_id:
                self.get_category_by_id(request.parent_id)

            category = Category(
                name=request.name,
                slug=request.slug,
                parent_id=request.parent_id,
                description=request.description,
                display_order=request.display_order
            )

            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            return category

        except Exception:
            self.db.rollback()
            raise

    def update_category(self, category_id: int, request: UpdateCategoryRequest) -> Category:
        try:
            category = self.get_category_by_id(category_id)

            # Check circular reference khi update parent_id
            if request.parent_id is not None:
                self._validate_parent_id(category_id, request.parent_id)

            if request.name is not None:
                category.name = request.name

            if request.slug is not None:
                # Check if new slug exists (trừ category hiện tại)
                existing = self.db.query(Category).filter_by(
                    slug= request.slug
                ).filter(
                    Category.id != category_id
                ).first()
                if existing:
                    raise ConflictException("Slug already exists")
                category.slug = request.slug

            if request.parent_id is not None:
                category.parent_id = request.parent_id

            if request.description is not None:
                category.description = request.description

            if request.display_order is not None:
                category.display_order = request.display_order

            self.db.commit()
            self.db.refresh(category)
            return category

        except Exception:
            self.db.rollback()
            raise

    def _validate_parent_id(self, category_id: int, parent_id: int) -> None:
        """Validate parent_id để tránh circular reference"""
        # Không cho phép set parent là chính nó
        if parent_id == category_id:
            raise ConflictException("Category cannot be parent of itself")

        # Kiểm tra circular reference (category không thể là con của cháu nó)
        current_parent = parent_id
        visited = {category_id}

        while current_parent:
            if current_parent in visited:
                raise ConflictException("Circular reference detected")

            visited.add(current_parent)
            parent_cat = self.db.query(Category).filter_by(id= current_parent).first()

            if not parent_cat:
                break

            current_parent = parent_cat.parent_id

    def delete_category(self, category_id: int) -> Dict[str, str]:
        try:
            category = self.get_category_by_id(category_id)

            # Check if category has children
            children = self.db.query(Category).filter_by(parent_id= category_id).first()
            if children:
                raise ConflictException("Cannot delete category with children")

            self.db.delete(category)
            self.db.commit()
            return {"message": "Category deleted successfully"}

        except Exception:
            self.db.rollback()
            raise