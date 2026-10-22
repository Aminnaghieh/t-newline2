"""
ingest.py – Import CSV files from the Torob dataset into SQLite database.
Run this once: python -m backend.ingest
"""

import csv
import json
import os
import sqlite3
import sys
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "torob.db")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "starcoach-dataset-v16-cap300-csv")


def create_tables(conn: sqlite3.Connection):
    """Create all tables and indexes."""
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS products_fts;
        DROP TABLE IF EXISTS offers;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS shops;

        CREATE TABLE shops (
            shop_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            location_label TEXT,
            lat REAL,
            lon REAL,
            category_names TEXT,
            weekly_hours TEXT,
            payment_options TEXT,
            contacts TEXT,
            instagram TEXT,
            website_url TEXT,
            supports_fast_delivery TEXT
        );

        CREATE TABLE products (
            product_id TEXT PRIMARY KEY,
            persian_title TEXT,
            brand_name TEXT,
            category_name TEXT,
            image_urls TEXT,
            specs TEXT,
            model TEXT
        );

        CREATE TABLE offers (
            offer_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            shop_id TEXT NOT NULL,
            price_toman INTEGER DEFAULT 0,
            seller_title TEXT,
            description TEXT,
            warranty TEXT,
            last_price_changed_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (shop_id) REFERENCES shops(shop_id)
        );

        -- Indexes for fast lookups
        CREATE INDEX idx_offers_product ON offers(product_id);
        CREATE INDEX idx_offers_shop ON offers(shop_id);
        CREATE INDEX idx_offers_price ON offers(price_toman);
        CREATE INDEX idx_shops_lat_lon ON shops(lat, lon);
        CREATE INDEX idx_products_category ON products(category_name);
        CREATE INDEX idx_products_brand ON products(brand_name);

        -- FTS5 virtual table for product search
        CREATE VIRTUAL TABLE products_fts USING fts5(
            product_id UNINDEXED,
            persian_title,
            brand_name,
            category_name,
            content='products',
            content_rowid='rowid'
        );
    """)
    conn.commit()


def _safe_int(val: str) -> int:
    """Convert to int safely."""
    if not val or val == "null":
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val: str):
    """Convert to float safely."""
    if not val or val == "null":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val: str) -> str:
    """Handle null strings."""
    if val == "null" or val is None:
        return ""
    return val


def import_shops(conn: sqlite3.Connection):
    """Import shops.csv."""
    path = os.path.join(DATA_DIR, "shops.csv")
    print(f"  Importing shops from {path}...")
    t0 = time.time()

    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                r["shop_id"],
                _safe_str(r["name"]),
                _safe_str(r["address"]),
                _safe_str(r["location_label"]),
                _safe_float(r["lat"]),
                _safe_float(r["lon"]),
                _safe_str(r["category_names"]),
                _safe_str(r["weekly_hours"]),
                _safe_str(r["payment_options"]),
                _safe_str(r["contacts"]),
                _safe_str(r["instagram"]),
                _safe_str(r["website_url"]),
                _safe_str(r["supports_fast_delivery"]),
            ))

    conn.executemany(
        "INSERT INTO shops VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"  ✓ {len(rows)} shops imported in {time.time() - t0:.1f}s")


def import_products(conn: sqlite3.Connection):
    """Import products.csv."""
    path = os.path.join(DATA_DIR, "products.csv")
    print(f"  Importing products from {path}...")
    t0 = time.time()

    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                r["product_id"],
                _safe_str(r["persian_title"]),
                _safe_str(r["brand_name"]),
                _safe_str(r["category_name"]),
                _safe_str(r["image_urls"]),
                _safe_str(r["specs"]),
                _safe_str(r.get("model", "")),
            ))

    conn.executemany(
        "INSERT INTO products VALUES (?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"  ✓ {len(rows)} products imported in {time.time() - t0:.1f}s")

    # Populate FTS index
    print("  Building FTS5 index...")
    t1 = time.time()
    conn.execute("""
        INSERT INTO products_fts(product_id, persian_title, brand_name, category_name)
        SELECT product_id, persian_title, brand_name, category_name
        FROM products
    """)
    conn.commit()
    print(f"  ✓ FTS5 index built in {time.time() - t1:.1f}s")


def import_offers(conn: sqlite3.Connection):
    """Import offers.csv."""
    path = os.path.join(DATA_DIR, "offers.csv")
    print(f"  Importing offers from {path}...")
    t0 = time.time()

    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((
                r["offer_id"],
                r["product_id"],
                r["shop_id"],
                _safe_int(r["price_toman"]),
                _safe_str(r["seller_title"]),
                _safe_str(r["description"]),
                _safe_str(r["warranty"]),
                _safe_str(r["last_price_changed_at"]),
            ))

    conn.executemany(
        "INSERT INTO offers VALUES (?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"  ✓ {len(rows)} offers imported in {time.time() - t0:.1f}s")


def main():
    """Run full data ingestion pipeline."""
    print("=" * 60)
    print("TorobGard – Data Ingestion Pipeline")
    print("=" * 60)

    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Dataset directory not found: {DATA_DIR}")
        sys.exit(1)

    # Remove existing database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("PRAGMA cache_size=-128000;")  # 128 MB

    print("\n[1/4] Creating tables...")
    create_tables(conn)

    print("\n[2/4] Importing shops...")
    import_shops(conn)

    print("\n[3/4] Importing products...")
    import_products(conn)

    print("\n[4/4] Importing offers...")
    import_offers(conn)

    # Final stats
    shops_count = conn.execute("SELECT COUNT(*) FROM shops").fetchone()[0]
    products_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    offers_count = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

    db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)

    print("\n" + "=" * 60)
    print("✅ Ingestion complete!")
    print(f"   Shops:    {shops_count:,}")
    print(f"   Products: {products_count:,}")
    print(f"   Offers:   {offers_count:,}")
    print(f"   DB size:  {db_size_mb:.1f} MB")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
