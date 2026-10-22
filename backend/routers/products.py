"""
products.py – Product search and detail API endpoints.
"""

from fastapi import APIRouter, Query
from backend.services.search import (
    search_products,
    get_product_detail,
    get_categories,
    get_brands,
    search_products_count,
)

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/products/search")
async def products_search(
    q: str = Query("", description="Search query"),
    category: str = Query("", description="Category filter"),
    brand: str = Query("", description="Brand filter"),
    min_price: int = Query(0, description="Minimum price"),
    max_price: int = Query(0, description="Maximum price"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Search products with filters."""
    offset = (page - 1) * limit
    results = search_products(
        q=q, category=category, brand=brand,
        min_price=min_price, max_price=max_price,
        limit=limit, offset=offset,
    )
    total = search_products_count(q=q, category=category, brand=brand)
    return {"products": results, "total": total, "page": page, "limit": limit}


@router.get("/products/{product_id}")
async def product_detail(product_id: str):
    """Get product details."""
    result = get_product_detail(product_id)
    if not result:
        return {"error": "Product not found"}
    return result


@router.get("/categories")
async def categories(limit: int = Query(50, ge=1, le=200)):
    """List product categories."""
    return {"categories": get_categories(limit=limit)}


@router.get("/brands")
async def brands(
    category: str = Query("", description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
):
    """List brands, optionally filtered by category."""
    return {"brands": get_brands(category=category, limit=limit)}
