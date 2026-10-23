"""
models.py – Pydantic models for TorobGard API.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


# ─── Request Models ──────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    session_id: Optional[str] = None
    context: Optional[dict] = None


class ProductSearchParams(BaseModel):
    q: str = ""
    category: str = ""
    brand: str = ""
    min_price: int = 0
    max_price: int = 0
    page: int = 1
    limit: int = 20


class NearbyShopsParams(BaseModel):
    lat: float
    lon: float
    product_id: str = ""
    radius_km: float = 5.0
    bnpl_provider: str = ""
    only_open: bool = False
    sort_by: str = "distance"  # distance | price | score
    page: int = 1
    limit: int = 20


# ─── Response Models ─────────────────────────────────────────

class ProductBrief(BaseModel):
    product_id: str
    persian_title: str
    brand_name: str = ""
    category_name: str = ""
    image_url: str = ""
    min_price: int = 0
    max_price: int = 0
    offer_count: int = 0
    specs_summary: str = ""


class ProductDetail(ProductBrief):
    specs: list[dict] = []
    image_urls: list[str] = []


class ShopBrief(BaseModel):
    shop_id: str
    name: str
    address: str = ""
    location_label: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    distance_m: Optional[float] = None
    is_open: Optional[bool] = None
    open_status: str = ""  # "باز", "بسته", "۱ ساعت دیگر می‌بندد"
    mall_info: Optional[MallInfo] = None
    bnpl_providers: list[str] = []
    has_bnpl: bool = False
    contacts: list[dict] = []
    instagram: str = ""
    website_url: str = ""


class MallInfo(BaseModel):
    mall_name: str = ""
    floor: str = ""
    unit: str = ""
    hallway: str = ""
    raw_address: str = ""


# Rebuild ShopBrief to resolve forward ref
ShopBrief.model_rebuild()


class ShopOffer(BaseModel):
    offer_id: str
    product_id: str
    persian_title: str = ""
    price_toman: int = 0
    price_display: str = ""
    warranty: str = ""
    seller_title: str = ""
    last_price_changed_at: str = ""
    price_age_days: int = 0
    price_freshness: str = ""  # "تازه", "نسبتاً قدیمی", "قدیمی"


class CompareItem(BaseModel):
    shop: ShopBrief
    offer: ShopOffer
    score: float = 0.0  # composite ranking score


class MapMarker(BaseModel):
    lat: float
    lon: float
    title: str
    shop_id: str = ""
    is_open: Optional[bool] = None
    price: int = 0


class ChatCard(BaseModel):
    type: str  # "product_list" | "shop_list" | "comparison" | "shop_detail" | "product_detail" | "mall_guide" | "verification"
    data: dict = {}


class ChatResponse(BaseModel):
    message: str
    step: str = ""  # "greeting" | "discovery" | "location" | "comparison" | "verification" | "fallback"
    cards: list[ChatCard] = []
    # Generative-UI blocks (validated server-side, see services/ui_schema.py).
    # Kept additive: `cards` keeps working for the current frontend.
    ui: list[dict] = []
    suggestions: list[str] = []
    map_markers: list[MapMarker] = []
    filters: dict = {}
    session_id: str = ""
    llm_used: bool = False   # True when the LLM-orchestrated path produced this reply
