"""
main.py – FastAPI application entry point for TorobGard.
Serves both the API and the frontend static files with production security hardening.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import db_exists
from backend.routers import chat, products, shops
from backend.security import SecurityMiddleware, resolve_safe_static_path


def _warmup():
    """Idempotent startup warm-up (runs in a background thread).

    1. (Re)create hot-path indexes.
    2. Warm the heaviest catalog queries once.
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
        search_products(q="کفش کتونی", limit=8)
        search_products(q="کفش کتونی", limit=8, lat=35.695, lon=51.406, radius_km=5.0)
        search_products(q="", limit=8, lat=35.695, lon=51.406, radius_km=5.0)
        search_products(q="", limit=8, lat=35.7789, lon=51.3767, radius_km=5.0)
    except Exception as e:
        logging.warning(f"Database warmup skipped/failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    threading.Thread(target=_warmup, name="torobgard-warmup", daemon=True).start()
    yield


app = FastAPI(
    title="ترب‌گرد | TorobGard",
    description="دستیار هوشمند خرید حضوری تهران",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── 1. Security & Rate Limiting Middleware ────────────────────
app.add_middleware(SecurityMiddleware)

# ─── 2. CORS Configuration ────────────────────────────────────
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ─── 3. Global Exception Handler (Prevent Info Leakage) ────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Internal error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "خطای غیرمنتظره در سرور رخ داده است. لطفاً مجدداً تلاش کنید."},
    )


# ─── 4. Register API Routers ──────────────────────────────────
app.include_router(chat.router)
app.include_router(products.router)
app.include_router(shops.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db_ready": db_exists()}


# ─── 5. Serve Frontend Static Files (Path Traversal Protected) ─
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
INDEX_FILE = os.path.join(STATIC_DIR, "index.html")

if os.path.exists(STATIC_DIR) and os.listdir(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes with directory traversal prevention."""
        if full_path:
            safe_file = resolve_safe_static_path(STATIC_DIR, full_path)
            if safe_file:
                return FileResponse(safe_file)
        return FileResponse(INDEX_FILE)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
