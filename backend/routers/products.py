"""
products.py – Product search and detail API endpoints.
"""

from fastapi import APIRouter, Query, Path
from backend.services.search import (
    search_products,
    search_products_located,
    get_product_detail,
    get_categories,
    get_brands,
    search_products_count,
)

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/products/search")
async def products_search(
    q: str = Query("", max_length=200, description="Search query"),
    category: str = Query("", max_length=100, description="Category filter"),
    brand: str = Query("", max_length=100, description="Brand filter"),
    min_price: int = Query(0, ge=0, le=10_000_000_000, description="Minimum price"),
    max_price: int = Query(0, ge=0, le=10_000_000_000, description="Maximum price"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    lat: float = Query(None, ge=-90.0, le=90.0, description="User latitude (enables location-aware results)"),
    lon: float = Query(None, ge=-180.0, le=180.0, description="User longitude (enables location-aware results)"),
    radius_km: float = Query(5.0, ge=0.1, le=1000.0, description="Nearby radius in km (capped at 25)"),
    sort: str = Query("distance", max_length=20, description="Located sort: distance | price"),
):
    """Search products with filters.

    Without lat/lon the response is identical to the original behavior.
    With lat/lon each product carries nearby fields and the response adds
    `radius_used` and `fallback`.
    """
    offset = (page - 1) * limit
    if lat is None or lon is None:
        results = search_products(
            q=q, category=category, brand=brand,
            min_price=min_price, max_price=max_price,
            limit=limit, offset=offset,
        )
        total = search_products_count(q=q, category=category, brand=brand)
        return {"products": results, "total": total, "page": page, "limit": limit}

    meta = search_products_located(
        q=q, category=category, brand=brand,
        min_price=min_price, max_price=max_price,
        limit=limit, offset=offset,
        lat=lat, lon=lon, radius_km=radius_km, sort=sort,
    )
    return {
        "products": meta["products"],
        "total": meta["total"],
        "total_capped": meta["total_capped"],
        "page": page,
        "limit": limit,
        "radius_used": meta["radius_used"],
        "fallback": meta["fallback"],
    }


@router.get("/products/{product_id}")
async def product_detail(
    product_id: str = Path(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
):
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
    category: str = Query("", max_length=100, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
):
    """List brands, optionally filtered by category."""
    return {"brands": get_brands(category=category, limit=limit)}
