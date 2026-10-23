"""
search.py – Product & shop search engine using SQLite FTS5.
"""

from backend.database import query, query_one
import json
import re
import threading
import time


def _normalize_query(q: str) -> str:
    """Normalize Persian query for FTS matching."""
    q = q.strip()
    # Replace common Persian chars
    q = q.replace("ي", "ی").replace("ك", "ک")
    q = q.replace("ئ", "ی")
    # Remove extra spaces
    q = re.sub(r"\s+", " ", q)
    return q


def _fts_query(q: str) -> str:
    """
    Convert user query to an FTS5 query string.

    Uses OR between tokens instead of AND: a real user query such as
    «کتونی راحت برای پیاده روی تا ۳ میلیون» contains many tokens that will
    never all appear in a single product title. OR + bm25 ranking keeps the
    most relevant products at the top instead of returning zero rows.
    """
    q = _normalize_query(q)
    tokens = q.split()
    # Use prefix matching for each token
    parts = [f'"{t}"*' for t in tokens if len(t) >= 2]
    return " OR ".join(parts) if parts else q


def search_products(
    q: str = "",
    category: str = "",
    brand: str = "",
    min_price: int = 0,
    max_price: int = 0,
    limit: int = 20,
    offset: int = 0,
    lat: float = None,
    lon: float = None,
    radius_km: float = 5.0,
    sort: str = "distance",
) -> list[dict]:
    """Search products with optional filters. Returns products with price range.

    When lat/lon are provided the result is location-aware (see
    `search_products_located`); without them behavior is identical to the
    original relevance-ranked search.
    """
    if lat is not None and lon is not None:
        return search_products_located(
            q=q, category=category, brand=brand, min_price=min_price,
            max_price=max_price, limit=limit, offset=offset,
            lat=lat, lon=lon, radius_km=radius_km, sort=sort,
        )["products"]

    conditions = []
    params = []

    # ── Full-text search ──────────────────────────────────────
    # The FTS5 table is joined (not an IN-subquery) so we can rank by bm25.
    join_fts = ""
    fts_params: list = []
    rank_expr = "0"
    if q:
        # NOTE: the FTS table must be referenced by its real name (no alias) –
        # SQLite cannot resolve `MATCH` against an aliased FTS5 table.
        join_fts = (
            "JOIN products_fts ON products_fts.product_id = p.product_id "
            "AND products_fts MATCH ?"
        )
        fts_params.append(_fts_query(q))
        # bm25() returns a negative score – the more negative, the better match.
        # Weights: title, brand, category (product_id is UNINDEXED).
        rank_expr = "bm25(products_fts, 10.0, 5.0, 3.0, 1.0)"

    if category:
        conditions.append("p.category_name LIKE ?")
        params.append(f"%{category}%")

    if brand:
        conditions.append("p.brand_name LIKE ?")
        params.append(f"%{brand}%")

    # Price filters must match *any* offer of the product inside the range,
    # not the aggregated min/max of the whole product.
    if min_price > 0 or max_price > 0:
        offer_conditions = ["price_toman > 0"]
        offer_params: list = []
        if min_price > 0:
            offer_conditions.append("price_toman >= ?")
            offer_params.append(min_price)
        if max_price > 0:
            offer_conditions.append("price_toman <= ?")
            offer_params.append(max_price)
        conditions.append(
            "EXISTS (SELECT 1 FROM offers f2 WHERE f2.product_id = p.product_id AND "
            + " AND ".join(offer_conditions)
            + ")"
        )
        params.extend(offer_params)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Price aggregate is computed only over the in-range offers when a budget
    # was given, so the displayed "starting price" respects the budget.
    agg_where = ""
    agg_params: list = []
    if min_price > 0 or max_price > 0:
        agg_where = "WHERE price_toman > 0"
        if min_price > 0:
            agg_where += " AND price_toman >= ?"
            agg_params.append(min_price)
        if max_price > 0:
            agg_where += " AND price_toman <= ?"
            agg_params.append(max_price)

    sql = f"""
        SELECT
            p.product_id, p.persian_title, p.brand_name, p.category_name,
            p.image_urls, p.specs,
            COALESCE(o.min_price, 0) as min_price,
            COALESCE(o.max_price, 0) as max_price,
            COALESCE(o.offer_count, 0) as offer_count,
            {rank_expr} as relevance
        FROM products p
        {join_fts}
        LEFT JOIN (
            SELECT product_id,
                   MIN(price_toman) as min_price,
                   MAX(price_toman) as max_price,
                   COUNT(*) as offer_count
            FROM offers
            {agg_where}
            GROUP BY product_id
        ) o ON p.product_id = o.product_id
        {where}
        ORDER BY relevance ASC, o.offer_count DESC, p.product_id
        LIMIT ? OFFSET ?
    """
    # Parameter order must follow the order of placeholders in the SQL text:
    # JOIN (fts) -> LEFT JOIN aggregate (agg) -> WHERE (conditions) -> LIMIT/OFFSET
    all_params = fts_params + agg_params + params + [limit, offset]

    rows = query(sql, tuple(all_params))
    results = []
    for r in rows:
        # Parse first image
        images = []
        try:
            images = json.loads(r["image_urls"]) if r["image_urls"] else []
        except (json.JSONDecodeError, TypeError):
            pass

        # Parse specs summary (first 3 specs)
        specs_summary = ""
        try:
            specs_list = json.loads(r["specs"]) if r["specs"] else []
            if isinstance(specs_list, list):
                parts = []
                for s in specs_list[:3]:
                    if isinstance(s, dict) and "key" in s and "value" in s:
                        parts.append(f"{s['key']}: {s['value']}")
                specs_summary = " | ".join(parts)
        except (json.JSONDecodeError, TypeError):
            pass

        results.append({
            "product_id": r["product_id"],
            "persian_title": r["persian_title"] or "",
            "brand_name": r["brand_name"] or "",
            "category_name": r["category_name"] or "",
            "image_url": images[0] if images else "",
            "image_urls": images,
            "min_price": r["min_price"] or 0,
            "max_price": r["max_price"] or 0,
            "offer_count": r["offer_count"] or 0,
            "specs_summary": specs_summary,
        })
    return results


def get_product_detail(product_id: str) -> dict | None:
    """Get full product details including specs."""
    row = query_one(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    )
    if not row:
        return None

    images = []
    try:
        images = json.loads(row["image_urls"]) if row["image_urls"] else []
    except (json.JSONDecodeError, TypeError):
        pass

    specs = []
    try:
        specs = json.loads(row["specs"]) if row["specs"] else []
    except (json.JSONDecodeError, TypeError):
        pass

    # Get price range from offers
    price_info = query_one(
        """SELECT MIN(price_toman) as min_price, MAX(price_toman) as max_price,
                  COUNT(*) as offer_count
           FROM offers WHERE product_id = ? AND price_toman > 0""",
        (product_id,),
    )

    return {
        "product_id": row["product_id"],
        "persian_title": row["persian_title"] or "",
        "brand_name": row["brand_name"] or "",
        "category_name": row["category_name"] or "",
        "image_url": images[0] if images else "",
        "image_urls": images,
        "specs": specs if isinstance(specs, list) else [],
        "min_price": price_info["min_price"] or 0 if price_info else 0,
        "max_price": price_info["max_price"] or 0 if price_info else 0,
        "offer_count": price_info["offer_count"] or 0 if price_info else 0,
    }


def get_categories(limit: int = 50) -> list[dict]:
    """Get top product categories by product count."""
    return query(
        """SELECT category_name, COUNT(*) as cnt
           FROM products
           WHERE category_name IS NOT NULL AND category_name != 'null'
           GROUP BY category_name
           ORDER BY cnt DESC
           LIMIT ?""",
        (limit,),
    )


def get_brands(category: str = "", limit: int = 50) -> list[dict]:
    """Get brands, optionally filtered by category."""
    if category:
        return query(
            """SELECT brand_name, COUNT(*) as cnt
               FROM products
               WHERE brand_name IS NOT NULL AND brand_name != 'null'
                 AND category_name LIKE ?
               GROUP BY brand_name ORDER BY cnt DESC LIMIT ?""",
            (f"%{category}%", limit),
        )
    return query(
        """SELECT brand_name, COUNT(*) as cnt
           FROM products
           WHERE brand_name IS NOT NULL AND brand_name != 'null'
           GROUP BY brand_name ORDER BY cnt DESC LIMIT ?""",
        (limit,),
    )


# ─── Location-aware product search ────────────────────────────

RADIUS_CAP_KM = 25.0        # beyond this the dataset has no reliable coverage
FALLBACK_TARGET = 8         # fill the page up to this many products (UI page size)
FALLBACK_MAX_PER_SHOP = 3   # fallback fill: at most 3 products per nearest shop
_LOCATED_ROW_CAP = 400      # hard cap on candidate rows fetched before merging

# Small in-memory TTL cache for located searches. Keyed primarily by
# (round(lat,3), round(lon,3), radius_km, q, sort); the remaining arguments
# are part of the key too so a cached entry can never be served for a
# request that differs in category/brand/price/window. The dataset is a
# static snapshot, so a long TTL is safe.
_LOCATED_CACHE: dict = {}
_LOCATED_CACHE_TTL_S = 1800.0   # 30 minutes
_LOCATED_CACHE_MAX = 256
_located_cache_lock = threading.Lock()


def _copy_located_meta(meta: dict) -> dict:
    """Shallow defensive copy of a cached located result (flat rows)."""
    return {**meta, "products": [dict(p) for p in meta["products"]]}


def _nearest_offer_for_product(product_id: str, lat: float, lon: float) -> dict | None:
    """Nearest shop offer (id + registered price) for one product, inside
    the 25 km cap. Uses the offers(product_id) index – one tiny query."""
    from backend.services.geo import bounding_box
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, RADIUS_CAP_KM)
    return query_one(
        """SELECT o.shop_id AS shop_id, o.price_toman AS price_toman
           FROM offers o
           JOIN shops s ON s.shop_id = o.shop_id
           WHERE o.product_id = ? AND o.price_toman > 0
             AND s.lat IS NOT NULL AND s.lon IS NOT NULL
             AND s.lat BETWEEN ? AND ? AND s.lon BETWEEN ? AND ?
           ORDER BY HAVERSINE_M(?, ?, s.lat, s.lon) ASC, o.price_toman ASC
           LIMIT 1""",
        (product_id, min_lat, max_lat, min_lon, max_lon, lat, lon),
    )


def _row_to_located_product(r: dict) -> dict:
    """Shape a located-search row into the product card contract, adding
    the nearby fields on top of the classic ones."""
    images = []
    try:
        images = json.loads(r["image_urls"]) if r["image_urls"] else []
    except (json.JSONDecodeError, TypeError):
        pass

    specs_summary = ""
    try:
        specs_list = json.loads(r["specs"]) if r["specs"] else []
        if isinstance(specs_list, list):
            parts = []
            for s in specs_list[:3]:
                if isinstance(s, dict) and "key" in s and "value" in s:
                    parts.append(f"{s['key']}: {s['value']}")
            specs_summary = " | ".join(parts)
    except (json.JSONDecodeError, TypeError):
        pass

    nearest = r["nearest_distance_m"]
    nearby_count = r["nearby_shops_count"] or 0
    in_radius = nearby_count > 0
    if in_radius:
        # Cheapest registered offer among the in-radius shops.
        min_price_nearby = r["min_price_nearby"] or 0
        display_price = min_price_nearby
    else:
        # Fallback item: no shop inside the radius. min_price_nearby is
        # intentionally null; nearest_shop_price is filled by the fallback
        # fill (see _nearest_offer_for_product).
        min_price_nearby = None
        display_price = 0
    return {
        "product_id": r["product_id"],
        "persian_title": r["persian_title"] or "",
        "brand_name": r["brand_name"] or "",
        "category_name": r["category_name"] or "",
        "image_url": images[0] if images else "",
        "min_price": display_price,
        "max_price": 0,
        "offer_count": nearby_count,
        "specs_summary": specs_summary,
        "nearby_shops_count": nearby_count,
        "min_price_nearby": min_price_nearby,
        "nearest_shop_price": None,
        "nearest_distance_m": round(nearest) if nearest is not None else None,
        "in_radius": in_radius,
    }


def search_products_located(
    q: str = "",
    category: str = "",
    brand: str = "",
    min_price: int = 0,
    max_price: int = 0,
    limit: int = 20,
    offset: int = 0,
    lat: float = None,
    lon: float = None,
    radius_km: float = 5.0,
    sort: str = "distance",
) -> dict:
    """Location-aware product search.

    Aggregates offers of shops inside the (capped) bounding box using a
    per-shop haversine prefilter, then groups per product:
      - nearby_shops_count / min_price_nearby: only shops within radius_km
      - nearest_distance_m: nearest shop inside the 25 km cap
    Products with no shop inside radius_km can still be returned as a
    fallback (in_radius=false, ordered by nearest distance) so the page is
    not empty when the dataset simply has no coverage there.

    Returns {"products", "radius_used", "fallback", "in_radius_count"}.
    """
    radius_km = max(0.1, min(float(radius_km or 5.0), RADIUS_CAP_KM))
    sort_key = "price" if sort == "price" else "distance"

    # TTL cache lookup – key includes the required components plus every
    # other argument so entries can never leak across differing requests.
    cache_key = (
        round(lat, 3), round(lon, 3), radius_km, q, sort,
        category, brand, min_price, max_price, limit, offset,
    )
    now = time.time()
    with _located_cache_lock:
        hit = _LOCATED_CACHE.get(cache_key)
        if hit and now - hit[0] <= _LOCATED_CACHE_TTL_S:
            return _copy_located_meta(hit[1])

    r_m = radius_km * 1000.0

    from backend.services.geo import bounding_box
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, RADIUS_CAP_KM)

    conditions = []
    params: list = []
    # NOTE: the FTS filter is applied inside the cand CTE (see fts_prefilter
    # below) so the aggregation only walks matching products' offers.
    if category:
        conditions.append("p.category_name LIKE ?")
        params.append(f"%{category}%")
    if brand:
        conditions.append("p.brand_name LIKE ?")
        params.append(f"%{brand}%")
    if min_price > 0:
        conditions.append("a.min_price_nearby >= ?")
        params.append(min_price)
    if max_price > 0:
        conditions.append("a.min_price_nearby <= ?")
        params.append(max_price)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    if not q:
        # Empty query: top products by number of nearby shops.
        order = (
            "(a.nearby_shops_count > 0) DESC, a.nearby_shops_count DESC, "
            "a.nearest_distance_m ASC, p.product_id"
        )
    elif sort_key == "price":
        order = (
            "(a.nearby_shops_count > 0) DESC, "
            "COALESCE(a.min_price_nearby, 9223372036854775807) ASC, "
            "a.nearest_distance_m ASC, p.product_id"
        )
    else:
        order = (
            "(a.nearby_shops_count > 0) DESC, a.nearest_distance_m ASC, "
            "a.nearby_shops_count DESC, p.product_id"
        )

    # Performance: when a text query is given, push the FTS filter INTO the
    # candidate CTE so the per-product aggregation only walks the offers of
    # matching products instead of the whole 330k+ offers table.
    fts_prefilter = ""
    fts_params: list = []
    if q:
        fts_prefilter = (
            "AND o.product_id IN "
            "(SELECT product_id FROM products_fts WHERE products_fts MATCH ?)"
        )
        fts_params.append(_fts_query(q))

    # Param order follows the textual order of placeholders:
    # shopd(haversine+box) -> cand(fts prefilter) -> agg(radius cases)
    # -> WHERE -> LIMIT
    sql = f"""
        WITH shopd AS (
            SELECT s.shop_id AS shop_id,
                   HAVERSINE_M(?, ?, s.lat, s.lon) AS dist_m
            FROM shops s
            WHERE s.lat IS NOT NULL AND s.lon IS NOT NULL
              AND s.lat BETWEEN ? AND ? AND s.lon BETWEEN ? AND ?
        ),
        cand AS (
            SELECT o.product_id AS product_id, o.shop_id AS shop_id,
                   o.price_toman AS price_toman, d.dist_m AS dist_m
            FROM offers o
            JOIN shopd d ON d.shop_id = o.shop_id
            WHERE o.price_toman > 0
            {fts_prefilter}
        ),
        agg AS (
            SELECT c.product_id AS product_id,
                   COUNT(DISTINCT CASE WHEN c.dist_m <= ? THEN c.shop_id END)
                       AS nearby_shops_count,
                   MIN(CASE WHEN c.dist_m <= ? THEN c.price_toman END)
                       AS min_price_nearby,
                   MIN(c.dist_m) AS nearest_distance_m
            FROM cand c
            GROUP BY c.product_id
        )
        SELECT p.product_id, p.persian_title, p.brand_name, p.category_name,
               p.image_urls, p.specs,
               a.nearby_shops_count, a.min_price_nearby,
               a.nearest_distance_m
        FROM agg a
        JOIN products p ON p.product_id = a.product_id
        {where}
        ORDER BY {order}
        LIMIT ?
    """
    all_params = (
        [lat, lon, min_lat, max_lat, min_lon, max_lon]
        + fts_params
        + [r_m, r_m]
        + params
        + [_LOCATED_ROW_CAP]
    )
    rows = query(sql, tuple(all_params))

    in_radius_rows = []
    fallback_pool = []
    for r in rows:
        rec = _row_to_located_product(r)
        if rec["in_radius"]:
            in_radius_rows.append(rec)
        else:
            fallback_pool.append(rec)

    target = max(limit, FALLBACK_TARGET)
    merged = list(in_radius_rows)
    fallback_used = False
    if len(merged) < target and fallback_pool:
        # Fill the page with out-of-radius products, walking the pool in
        # nearest-first order but capping at FALLBACK_MAX_PER_SHOP products
        # whose nearest shop is the same, so one shop cannot dominate the
        # list. Enriched lazily with the nearest shop's registered price.
        need = target - len(merged)
        filled = 0
        per_shop: dict[str, int] = {}
        for rec in fallback_pool:
            if filled >= need:
                break
            nearest = _nearest_offer_for_product(rec["product_id"], lat, lon)
            if not nearest:
                continue
            shop_id = nearest["shop_id"]
            if per_shop.get(shop_id, 0) >= FALLBACK_MAX_PER_SHOP:
                continue
            per_shop[shop_id] = per_shop.get(shop_id, 0) + 1
            rec["nearest_shop_price"] = nearest["price_toman"] or 0
            rec["min_price"] = rec["nearest_shop_price"]
            merged.append(rec)
            filled += 1
        fallback_used = filled > 0

    if offset > 0:
        page_items = merged[offset: offset + limit]
    else:
        page_items = merged[:limit]

    meta = {
        "products": page_items,
        "radius_used": radius_km,
        "fallback": fallback_used,
        "in_radius_count": len(in_radius_rows),
        "total": len(in_radius_rows),
        # The row cap bounds how many in-radius matches we ever count, so a
        # full cap means "400+" rather than an exact number.
        "total_capped": len(in_radius_rows) >= _LOCATED_ROW_CAP,
    }

    with _located_cache_lock:
        if len(_LOCATED_CACHE) >= _LOCATED_CACHE_MAX:
            expired = [k for k, v in _LOCATED_CACHE.items()
                       if now - v[0] > _LOCATED_CACHE_TTL_S]
            for k in expired:
                _LOCATED_CACHE.pop(k, None)
            while len(_LOCATED_CACHE) >= _LOCATED_CACHE_MAX:
                _LOCATED_CACHE.pop(next(iter(_LOCATED_CACHE)))
        _LOCATED_CACHE[cache_key] = (now, meta)
    return meta


def search_products_count(q: str = "", category: str = "", brand: str = "") -> int:
    """Count matching products."""
    conditions = []
    params = []
    if q:
        fts_q = _fts_query(q)
        conditions.append("product_id IN (SELECT product_id FROM products_fts WHERE products_fts MATCH ?)")
        params.append(fts_q)
    if category:
        conditions.append("category_name LIKE ?")
        params.append(f"%{category}%")
    if brand:
        conditions.append("brand_name LIKE ?")
        params.append(f"%{brand}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    row = query_one(f"SELECT COUNT(*) as cnt FROM products {where}", tuple(params))
    return row["cnt"] if row else 0
