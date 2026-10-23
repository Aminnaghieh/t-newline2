"""
main.py – FastAPI application entry point for TorobGard.
Serves both the API and the frontend static files.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import db_exists
from backend.routers import chat, products, shops


def _warmup():
    """Idempotent startup warm-up (runs in a background thread).

    1. (Re)create the hot-path indexes – CREATE INDEX IF NOT EXISTS is a
       no-op when they already exist. idx_offers_product_price is the
       covering index that fixes the classic no-location search (see below).
    2. Run the heaviest catalog queries once so the SQLite page cache is
       warm and the first real request is fast (observed ~14s cold → ~1s).
    Failures are swallowed: a missing database must not block startup.
    """
    try:
        from backend.database import get_conn
        conn = get_conn()
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_shops_lat_lon ON shops(lat, lon);
            CREATE INDEX IF NOT EXISTS idx_offers_shop ON offers(shop_id);
            CREATE INDEX IF NOT EXISTS idx_offers_product ON offers(product_id);
            CREATE INDEX IF NOT EXISTS idx_offers_product_price ON offers(product_id, price_toman);
        """)
        conn.commit()

        from backend.services.search import search_products
        # Warm only the paths the UI actually exercises, in the order they
        # are hit after a cold start. (The classic no-filter catalog query is
        # deliberately NOT warmed: the UI never issues it and it aggregates
        # the whole 225k-product table.)
        search_products(q="کفش کتونی", limit=8)                                  # classic text search
        search_products(q="کفش کتونی", limit=8, lat=35.695, lon=51.406,
                        radius_km=5.0)                                            # UI initial catalog (located)
        search_products(q="", limit=8, lat=35.695, lon=51.406, radius_km=5.0)     # located browse / fallback paths
        # Pre-populate the located-search TTL cache for the two reference
        # areas so their first real request is served from memory.
        search_products(q="", limit=8, lat=35.7789, lon=51.3767, radius_km=5.0)   # Saadat Abad (cache warm)
    except Exception:
        # Missing/empty database (e.g. fresh clone before ingest) – the app
        # must still boot; endpoints will surface the real state via /api/health.
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up in a background daemon thread so the server accepts requests
    # immediately. Requests that arrive before the warm-up finishes still
    # work – they just miss the cache/page-cache and run slower.
    import threading
    threading.Thread(target=_warmup, name="torobgard-warmup", daemon=True).start()
    yield


app = FastAPI(
    title="ترب‌گرد | TorobGard",
    description="دستیار هوشمند خرید حضوری تهران",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(chat.router)
app.include_router(products.router)
app.include_router(shops.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_ready": db_exists()}


# Serve frontend static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR) and os.listdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
