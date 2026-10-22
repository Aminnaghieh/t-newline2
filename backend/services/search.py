"""
search.py – Product & shop search engine using SQLite FTS5.
"""

from backend.database import query, query_one
import json
import re


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
) -> list[dict]:
    """Search products with optional filters. Returns products with price range."""

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
