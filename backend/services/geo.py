"""
geo.py – Geospatial utilities for distance calculation and nearby search.
Uses Haversine formula for accurate distance on Earth's surface.
"""

import math
from backend.database import query


EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters."""
    return haversine_km(lat1, lon1, lat2, lon2) * 1000


def bounding_box(lat: float, lon: float, radius_km: float):
    """Return (min_lat, max_lat, min_lon, max_lon) bounding box for a quick SQL filter."""
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lat - dlat, lat + dlat, lon - dlon, lon + dlon)


def find_nearby_shops(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
    product_id: str = "",
    bnpl_provider: str = "",
    only_open_sql: str = "",
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    """
    Find shops near a location, optionally filtered by product availability
    and BNPL provider. Returns shops sorted by distance.
    """
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

    conditions = [
        "s.lat BETWEEN ? AND ?",
        "s.lon BETWEEN ? AND ?",
    ]
    params: list = [min_lat, max_lat, min_lon, max_lon]

    join_clause = ""
    if product_id:
        join_clause = "INNER JOIN offers o ON s.shop_id = o.shop_id AND o.product_id = ?"
        params.insert(0, product_id)  # goes before lat/lon params? No, let's rebuild

    # Rebuild params properly
    params_list = []
    if product_id:
        join_clause = "INNER JOIN offers o ON s.shop_id = o.shop_id AND o.product_id = ?"
        params_list.append(product_id)

    params_list.extend([min_lat, max_lat, min_lon, max_lon])

    if bnpl_provider:
        conditions.append("s.payment_options LIKE ?")
        params_list.append(f"%{bnpl_provider}%")

    where = "WHERE " + " AND ".join(conditions)

    select_extra = ""
    if product_id:
        select_extra = ", o.price_toman, o.offer_id, o.warranty, o.last_price_changed_at, o.seller_title"

    sql = f"""
        SELECT s.*{select_extra}
        FROM shops s
        {join_clause}
        {where}
        LIMIT ? OFFSET ?
    """
    params_list.extend([limit * 3, offset])  # fetch more for post-sort

    rows = query(sql, tuple(params_list))

    # Calculate actual distances and sort
    enriched = []
    for r in rows:
        rd = dict(r) if not isinstance(r, dict) else r
        if rd.get("lat") and rd.get("lon"):
            dist = haversine_m(lat, lon, rd["lat"], rd["lon"])
            if dist <= radius_km * 1000:
                rd["distance_m"] = round(dist)
                enriched.append(rd)

    enriched.sort(key=lambda x: x["distance_m"])
    return enriched[offset : offset + limit]


def find_alternative_shops(
    current_shop_id: str,
    product_id: str,
    lat: float,
    lon: float,
    radius_km: float = 10.0,
    limit: int = 5,
) -> list[dict]:
    """
    Find alternative shops that carry the same product,
    excluding the current shop. Used for fallback suggestions.
    If no shops carry the exact same product, falls back to nearby shops
    in the same category.
    """
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

    sql = """
        SELECT s.*, o.price_toman, o.offer_id, o.warranty,
               o.last_price_changed_at, o.seller_title
        FROM shops s
        INNER JOIN offers o ON s.shop_id = o.shop_id
        WHERE o.product_id = ?
          AND s.shop_id != ?
          AND s.lat BETWEEN ? AND ?
          AND s.lon BETWEEN ? AND ?
          AND o.price_toman > 0
        GROUP BY s.shop_id
        ORDER BY o.price_toman ASC
    """
    rows = query(
        sql,
        (product_id, current_shop_id, min_lat, max_lat, min_lon, max_lon),
    )

    # If no matches in radius, try all of Tehran for exact product
    if not rows:
        sql_wide = """
            SELECT s.*, o.price_toman, o.offer_id, o.warranty,
                   o.last_price_changed_at, o.seller_title
            FROM shops s
            INNER JOIN offers o ON s.shop_id = o.shop_id
            WHERE o.product_id = ?
              AND s.shop_id != ?
              AND o.price_toman > 0
            GROUP BY s.shop_id
            ORDER BY o.price_toman ASC
            LIMIT 10
        """
        rows = query(sql_wide, (product_id, current_shop_id))

    # If still no matches, find shops with similar products in the same category
    if not rows:
        sql_cat = """
            SELECT s.*, o.price_toman, o.offer_id, o.warranty,
                   o.last_price_changed_at, o.seller_title
            FROM shops s
            INNER JOIN offers o ON s.shop_id = o.shop_id
            INNER JOIN products p ON o.product_id = p.product_id
            WHERE p.category_name IN (SELECT category_name FROM products WHERE product_id = ?)
              AND s.shop_id != ?
              AND s.lat BETWEEN ? AND ?
              AND s.lon BETWEEN ? AND ?
              AND o.price_toman > 0
            GROUP BY s.shop_id
            ORDER BY o.price_toman ASC
            LIMIT 10
        """
        rows = query(sql_cat, (product_id, current_shop_id, min_lat, max_lat, min_lon, max_lon))

    enriched = []
    seen = set()
    for r in rows:
        rd = dict(r) if not isinstance(r, dict) else r
        if rd["shop_id"] in seen:
            continue
        seen.add(rd["shop_id"])
        if rd.get("lat") and rd.get("lon"):
            rd["distance_m"] = round(haversine_m(lat, lon, rd["lat"], rd["lon"]))
            enriched.append(rd)

    enriched.sort(key=lambda x: x["distance_m"])
    return enriched[:limit]
