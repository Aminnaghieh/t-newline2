"""
shops.py – Shop search, nearby, and detail API endpoints.
"""

from fastapi import APIRouter, Query, Path
from backend.database import query, query_one
from backend.services.geo import haversine_m, bounding_box
from backend.services.hours import check_shop_status
from backend.services.mall import parse_mall_info, generate_mall_guide
from backend.services.payment import get_bnpl_providers
import json

router = APIRouter(prefix="/api", tags=["shops"])


@router.get("/shops/{shop_id}")
async def shop_detail(
    shop_id: str = Path(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
):
    """Get shop details."""
    shop = query_one("SELECT * FROM shops WHERE shop_id = ?", (shop_id,))
    if not shop:
        return {"error": "Shop not found"}

    hours_status = check_shop_status(shop.get("weekly_hours", ""))
    mall_info = parse_mall_info(shop.get("address", ""))
    bnpl = get_bnpl_providers(shop.get("payment_options", ""))

    contacts = []
    try:
        contacts = json.loads(shop.get("contacts", "[]")) if shop.get("contacts") else []
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        **dict(shop),
        "is_open": hours_status["is_open"],
        "open_status": hours_status["status_text"],
        "hours_detail": hours_status["detail"],
        "mall_info": mall_info,
        "mall_guide": generate_mall_guide(mall_info) if mall_info else "",
        "bnpl_providers": bnpl,
        "has_bnpl": len(bnpl) > 0,
        "contacts_parsed": contacts,
    }


@router.get("/shops/{shop_id}/offers")
async def shop_offers(
    shop_id: str = Path(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$"),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all product offers for a shop."""
    offset = (page - 1) * limit
    offers = query(
        """SELECT o.*, p.persian_title, p.brand_name, p.category_name, p.image_urls
           FROM offers o
           JOIN products p ON o.product_id = p.product_id
           WHERE o.shop_id = ? AND o.price_toman > 0
           ORDER BY o.price_toman ASC
           LIMIT ? OFFSET ?""",
        (shop_id, limit, offset),
    )

    results = []
    for o in offers:
        images = []
        try:
            images = json.loads(o["image_urls"]) if o.get("image_urls") else []
        except (json.JSONDecodeError, TypeError):
            pass

        results.append({
            "offer_id": o["offer_id"],
            "product_id": o["product_id"],
            "persian_title": o.get("persian_title", ""),
            "brand_name": o.get("brand_name", ""),
            "category_name": o.get("category_name", ""),
            "image_url": images[0] if images else "",
            "price_toman": o["price_toman"],
            "warranty": o.get("warranty", ""),
            "seller_title": o.get("seller_title", ""),
            "last_price_changed_at": o.get("last_price_changed_at", ""),
        })

    total = query_one(
        "SELECT COUNT(*) as cnt FROM offers WHERE shop_id = ? AND price_toman > 0",
        (shop_id,),
    )

    return {"offers": results, "total": total["cnt"] if total else 0, "page": page}


@router.get("/shops/nearby/search")
async def nearby_shops(
    lat: float = Query(..., ge=-90.0, le=90.0, description="User latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="User longitude"),
    radius: float = Query(5.0, ge=0.1, le=50.0, description="Radius in km"),
    product_id: str = Query("", max_length=64, description="Filter by product"),
    bnpl: str = Query("", max_length=64, description="Filter by BNPL provider"),
    only_open: bool = Query(False, description="Only open shops"),
    limit: int = Query(20, ge=1, le=100),
):
    """Find shops near a location."""
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius)

    conditions = ["s.lat BETWEEN ? AND ?", "s.lon BETWEEN ? AND ?"]
    params = [min_lat, max_lat, min_lon, max_lon]

    join = ""
    select_extra = ""
    if product_id:
        join = "INNER JOIN offers o ON s.shop_id = o.shop_id AND o.product_id = ? AND o.price_toman > 0"
        params.insert(0, product_id)
        select_extra = ", o.price_toman, o.offer_id, o.warranty, o.last_price_changed_at"

    if bnpl:
        conditions.append("s.payment_options LIKE ?")
        params.append(f"%{bnpl}%")

    where = "WHERE " + " AND ".join(conditions)
    sql = f"SELECT s.*{select_extra} FROM shops s {join} {where} LIMIT ?"
    params.append(limit * 3)

    rows = query(sql, tuple(params))

    results = []
    for r in rows:
        if not r.get("lat") or not r.get("lon"):
            continue
        dist = haversine_m(lat, lon, r["lat"], r["lon"])
        if dist > radius * 1000:
            continue

        hours = check_shop_status(r.get("weekly_hours", ""))
        if only_open and not hours["is_open"]:
            continue

        mall = parse_mall_info(r.get("address", ""))
        bnpl_list = get_bnpl_providers(r.get("payment_options", ""))

        results.append({
            "shop_id": r["shop_id"],
            "name": r["name"],
            "address": r.get("address", ""),
            "lat": r["lat"],
            "lon": r["lon"],
            "distance_m": round(dist),
            "is_open": hours["is_open"],
            "open_status": hours["status_text"],
            "mall_guide": generate_mall_guide(mall) if mall else "",
            "bnpl_providers": bnpl_list,
            "price_toman": r.get("price_toman", 0),
        })

    results.sort(key=lambda x: x["distance_m"])
    return {"shops": results[:limit], "total": len(results)}
