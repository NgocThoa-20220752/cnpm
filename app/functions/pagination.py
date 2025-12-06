from typing import TypeVar, Generic, List
from pydantic import BaseModel
from math import ceil

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    limit: int
    total_pages: int
    data: List[T]


def paginate(query, page: int, limit: int):
    """
    Paginate query results
    """
    total = query.count()
    total_pages = ceil(total / limit) if limit > 0 else 0

    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "data": items
    }