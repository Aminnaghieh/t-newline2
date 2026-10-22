"""
agent.py – The AI agent brain for TorobGard.
Implements a multi-step conversational flow for in-person shopping assistance.
Works as a rule-based smart agent with optional Gemini LLM enhancement.
"""

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.database import query, query_one
from backend.services.search import search_products, get_product_detail
from backend.services.geo import haversine_m, find_nearby_shops, find_alternative_shops
from backend.services.hours import check_shop_status, get_today_hours_text
from backend.services.mall import parse_mall_info, generate_mall_guide, is_same_mall
from backend.services.payment import get_bnpl_providers, has_bnpl, get_all_provider_names

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# ─── Session Storage (in-memory for hackathon) ─────────────
_sessions: dict[str, dict] = {}


def _get_session(session_id: str = "") -> dict:
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
    if session_id not in _sessions:
        _sessions[session_id] = {
            "id": session_id,
            "step": "greeting",
            "history": [],
            "selected_product": None,
            "selected_products": [],
            "user_lat": None,
            "user_lon": None,
            "budget_min": 0,
            "budget_max": 0,
            "needs": [],
            "category": "",
            "brand": "",
            "bnpl_required": False,
            "bnpl_provider": "",
            "radius_km": 5.0,
        }
    return _sessions[session_id]


# ─── Intent Detection ──────────────────────────────────────

def _detect_intent(message: str) -> dict:
    """Detect user intent from message text."""
    msg = message.strip().lower()
    msg_orig = message.strip()

    intent = {
        "type": "unknown",
        "search_query": "",
        "category": "",
        "brand": "",
        "budget": 0,
        "budget_text": "",
        "wants_bnpl": False,
        "bnpl_provider": "",
        "lat": None,
        "lon": None,
        "area": "",
        "product_id": "",
        "shop_id": "",
    }

    # Check for greeting
    greetings = ["سلام", "درود", "هلو", "hi", "hello", "شروع"]
    if any(g in msg for g in greetings) and len(msg) < 30:
        intent["type"] = "greeting"
        return intent

    # Check for BNPL / installment
    bnpl_keywords = ["قسط", "اقساط", "قسطی", "اعتبار", "اعتباری", "اسنپ پی", "اسنپ‌پی", "تارا", "دیجی پی", "ازکی"]
    for kw in bnpl_keywords:
        if kw in msg:
            intent["wants_bnpl"] = True
            if "اسنپ" in msg:
                intent["bnpl_provider"] = "اسنپ‌پی"
            elif "تارا" in msg:
                intent["bnpl_provider"] = "تارا"
            elif "دیجی" in msg:
                intent["bnpl_provider"] = "دیجی پی"
            elif "ازکی" in msg:
                intent["bnpl_provider"] = "ازکی‌وام"
            break

    # Check for budget
    budget_patterns = [
        r"بودجه[ام]?\s*(?:حدود|تا|زیر)?\s*(\d[\d,/.]*)\s*(تومن|تومان|میلیون|ملیون|هزار|k|m)?",
        r"(\d[\d,/.]*)\s*(تومن|تومان|میلیون|ملیون|هزار|k|m)",
        r"(?:تا|حداکثر|زیر)\s*(\d[\d,/.]*)\s*(تومن|تومان|میلیون|ملیون|هزار|k|m)?",
    ]
    for pattern in budget_patterns:
        m = re.search(pattern, msg_orig)
        if m:
            amount_str = m.group(1).replace(",", "").replace("/", ".")
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            unit = m.group(2) if m.lastindex >= 2 and m.group(2) else ""
            if unit in ("میلیون", "ملیون", "m"):
                amount *= 1_000_000
            elif unit in ("هزار", "k"):
                amount *= 1_000
            elif amount < 1000:
                # Assume millions if small number
                amount *= 1_000_000
            intent["budget"] = int(amount)
            intent["budget_text"] = f"{int(amount):,} تومان"
            break

    # Check for location/area mentions
    areas = {
        "سعادت‌آباد": (35.7789, 51.3767), "سعادت آباد": (35.7789, 51.3767),
        "تجریش": (35.8033, 51.4268), "ونک": (35.7589, 51.4011),
        "ولیعصر": (35.7144, 51.4103), "فاطمی": (35.7210, 51.3964),
        "جمهوری": (35.6950, 51.4060), "انقلاب": (35.7003, 51.3964),
        "پونک": (35.7630, 51.3475), "شهرک غرب": (35.7615, 51.3597),
        "صادقیه": (35.7186, 51.3317), "آزادی": (35.6998, 51.3370),
        "مجیدیه": (35.7387, 51.4596), "نارمک": (35.7386, 51.4786),
        "پاسداران": (35.7674, 51.4597), "تهرانپارس": (35.7310, 51.4980),
        "هفت‌تیر": (35.7143, 51.4229), "هفت تیر": (35.7143, 51.4229),
        "چارسو": (35.6950, 51.4060), "علاءالدین": (35.6950, 51.4060),
        "علاالدین": (35.6950, 51.4060), "بازار بزرگ": (35.6740, 51.4200),
        "لاله‌زار": (35.6930, 51.4020), "راه آهن": (35.6900, 51.3950),
        "مولوی": (35.6870, 51.4000), "خیابان ری": (35.6800, 51.4100),
    }
    for area_name, (lat, lon) in areas.items():
        if area_name in msg_orig:
            intent["area"] = area_name
            intent["lat"] = lat
            intent["lon"] = lon
            break

    # Check for product search intent
    search_words = msg_orig
    # Remove budget and area text
    for pattern in budget_patterns:
        search_words = re.sub(pattern, "", search_words)
    for area in areas:
        search_words = search_words.replace(area, "")

    # Remove BNPL provider names – they are a filter, not part of the product
    for provider in ("اسنپ‌پی", "اسنپ پی", "اسنپپی", "دیجی پی", "دیجی‌پی", "ازکی‌وام", "ازکی وام", "ترب‌پی"):
        search_words = search_words.replace(provider, "")
    # Remove generic BNPL words
    for kw in ("اقساطی", "اقساط", "قسطی", "قسط", "اعتباری", "اعتبار", "خرید"):
        search_words = search_words.replace(kw, "")

    # Remove common filler tokens (exact word match, not substring!)
    filler_set = {
        "می‌خوام", "میخوام", "میخواهم", "می‌خواهم", "نیاز", "دارم", "دنبال", "پیدا", "کن", "نشون", "بده",
        "لطفاً", "لطفا", "ممنون", "برام", "بهم", "یه", "یک", "دو", "سه",
        "خوب", "خوبه", "مناسب", "ارزان", "ارزون", "گرون", "بهترین",
        "بخرم", "بخر", "قیمت", "فروشگاه", "مغازه", "تا", "حدود", "زیر", "سقف",
        "پاساژ", "کجا", "چطور", "چی", "کدوم", "کدام", "با", "از", "در",
        "تومان", "تومن", "میلیون", "ملیون", "هزار",
        "برای", "پیاده", "روی", "راه", "رفتن", "استفاده", "کنم", "شود",
        "نزدیک", "اطراف", "این", "آن", "همین", "الان", "بهمراه", "همراه",
        "راحت", "خوبه", "می‌کنه", "میشه", "باشد", "هست", "بود",
    }
    tokens = [w for w in search_words.split() if w not in filler_set]
    search_words = " ".join(tokens).strip()
    # Collapse duplicated whitespace left behind by token removal
    search_words = re.sub(r"\s+", " ", search_words).strip()

    if len(search_words) >= 2:
        intent["type"] = "search"
        intent["search_query"] = search_words
    elif intent["wants_bnpl"]:
        intent["type"] = "bnpl_filter"
    elif intent.get("area"):
        intent["type"] = "area_search"

    return intent


# ─── Price Formatting ──────────────────────────────────────

def _format_price(price: int) -> str:
    """Format price in toman to readable Persian string."""
    if price <= 0:
        return "نامشخص"
    if price >= 1_000_000:
        millions = price / 1_000_000
        if millions == int(millions):
            return f"{int(millions):,} میلیون تومان"
        return f"{millions:,.1f} میلیون تومان"
    return f"{price:,} تومان"


def _price_age_info(last_changed: str) -> dict:
    """Calculate price age and freshness indicator."""
    if not last_changed or last_changed == "null":
        return {"days": -1, "label": "نامشخص", "color": "gray"}
    try:
        dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - dt).days
        if days <= 7:
            return {"days": days, "label": "به‌روز", "color": "green"}
        elif days <= 30:
            return {"days": days, "label": f"{days} روز پیش", "color": "yellow"}
        else:
            return {"days": days, "label": f"{days} روز پیش (قدیمی)", "color": "red"}
    except Exception:
        return {"days": -1, "label": "نامشخص", "color": "gray"}


# ─── Core Agent Logic ──────────────────────────────────────

def process_message(
    message: str,
    session_id: str = "",
    lat: float = None,
    lon: float = None,
    context: dict = None,
) -> dict:
    """
    Process a user message and return a structured response.
    This is the main entry point for the agent.
    """
    session = _get_session(session_id)
    session_id = session["id"]

    # Update location if provided
    has_explicit_location = bool(lat and lon)
    if has_explicit_location:
        session["user_lat"] = lat
        session["user_lon"] = lon

    # Handle context actions (from UI buttons/cards)
    if context:
        return _handle_context_action(session, context)

    # Detect intent
    intent = _detect_intent(message)

    # Update session from intent
    if intent.get("budget"):
        session["budget_max"] = intent["budget"]
    if intent.get("wants_bnpl"):
        session["bnpl_required"] = True
        session["bnpl_provider"] = intent.get("bnpl_provider", "")
    if intent.get("lat") and intent.get("lon"):
        session["user_lat"] = intent["lat"]
        session["user_lon"] = intent["lon"]

    # Add to history
    session["history"].append({"role": "user", "content": message})

    # Route to appropriate handler
    if intent["type"] == "greeting":
        return _handle_greeting(session)
    elif intent["type"] == "search":
        return _handle_search(session, intent)
    elif intent["type"] == "bnpl_filter":
        return _handle_bnpl_query(session, intent)
    elif intent["type"] == "area_search":
        return _handle_area_search(session, intent)
    else:
        # Try search with the full message
        intent["search_query"] = message.strip()
        intent["type"] = "search"
        return _handle_search(session, intent)


def _handle_greeting(session: dict) -> dict:
    session["step"] = "greeting"
    return {
        "message": "سلام! 👋 من **ترب‌گرد** هستم، دستیار هوشمند خرید حضوری شما.\n\nبه من بگید دنبال چه محصولی هستید؟ مثلاً:\n• کفش کتونی نایک\n• گوشی سامسونگ\n• لپ‌تاپ برای برنامه‌نویسی",
        "step": "greeting",
        "cards": [],
        "suggestions": [
            "کفش کتونی مردانه",
            "گوشی موبایل",
            "لپ‌تاپ",
            "هدفون بلوتوثی",
            "ساعت هوشمند",
        ],
        "map_markers": [],
        "filters": {},
        "session_id": session["id"],
    }


def _handle_search(session: dict, intent: dict) -> dict:
    """Handle product search requests."""
    q = intent.get("search_query", "")
    max_price = intent.get("budget", session.get("budget_max", 0))

    # Search products
    results = search_products(
        q=q,
        category=intent.get("category", ""),
        brand=intent.get("brand", ""),
        min_price=0,
        max_price=max_price,
        limit=12,
    )

    if not results:
        return {
            "message": f"متأسفانه محصولی با عنوان «{q}» پیدا نشد. لطفاً عبارت دیگری را امتحان کنید یا دسته‌بندی مورد نظرتان را بگویید.",
            "step": "discovery",
            "cards": [],
            "suggestions": ["کفش ورزشی", "گوشی موبایل", "لپ‌تاپ", "هدفون"],
            "map_markers": [],
            "filters": {},
            "session_id": session["id"],
        }

    session["step"] = "discovery"

    # Build product cards
    products_data = []
    for p in results:
        products_data.append({
            "product_id": p["product_id"],
            "persian_title": p["persian_title"],
            "brand_name": p["brand_name"],
            "category_name": p["category_name"],
            "image_url": p.get("image_url", ""),
            "min_price": p["min_price"],
            "max_price": p["max_price"],
            "min_price_display": _format_price(p["min_price"]),
            "max_price_display": _format_price(p["max_price"]),
            "offer_count": p["offer_count"],
            "specs_summary": p.get("specs_summary", ""),
        })

    budget_text = ""
    if max_price > 0:
        budget_text = f" (بودجه: {_format_price(max_price)})"

    msg = f"**{len(results)} محصول** برای «{q}»{budget_text} پیدا شد.\n\nمحصول مورد نظرتان را انتخاب کنید تا فروشگاه‌های حضوری نزدیک شما را پیدا کنم. 🏪"

    return {
        "message": msg,
        "step": "discovery",
        "cards": [{"type": "product_list", "data": {"products": products_data, "query": q}}],
        "suggestions": [],
        "map_markers": [],
        "filters": {
            "query": q,
            "budget_max": max_price,
        },
        "session_id": session["id"],
    }


def _handle_context_action(session: dict, context: dict) -> dict:
    """Handle actions triggered from UI elements (product selection, shop selection, etc.)."""
    action = context.get("action", "")

    # Filters coming from the UI take precedence over the ones stored in the
    # session (which were parsed from the chat message).
    if context.get("radius_km"):
        session["radius_km"] = float(context["radius_km"])
    if "bnpl_provider" in context:
        provider = (context.get("bnpl_provider") or "").strip()
        session["bnpl_provider"] = provider
        session["bnpl_required"] = bool(provider)

    if action == "select_product":
        return _handle_product_selected(session, context.get("product_id", ""))
    elif action == "find_shops":
        return _handle_find_shops(session, context.get("product_id", ""))
    elif action == "select_shop":
        return _handle_shop_selected(session, context.get("shop_id", ""), context.get("product_id", ""))
    elif action == "verify_shop":
        return _handle_verify_shop(session, context.get("shop_id", ""), context.get("product_id", ""))
    elif action == "find_alternatives":
        return _handle_find_alternatives(session, context.get("shop_id", ""), context.get("product_id", ""))
    elif action == "compare_shops":
        return _handle_compare_shops(session, context.get("product_id", ""))

    return _handle_greeting(session)


def _handle_product_selected(session: dict, product_id: str) -> dict:
    """Handle when user selects a specific product."""
    product = get_product_detail(product_id)
    if not product:
        return {"message": "محصول مورد نظر یافت نشد.", "step": "discovery", "cards": [], "suggestions": [], "map_markers": [], "filters": {}, "session_id": session["id"]}

    session["selected_product"] = product
    session["step"] = "location"

    # Check if we have user location
    has_location = session.get("user_lat") and session.get("user_lon")

    msg = f"**{product['persian_title']}**\n\n"
    if product.get("brand_name"):
        msg += f"برند: {product['brand_name']}\n"
    msg += f"بازه قیمت: {_format_price(product['min_price'])} تا {_format_price(product['max_price'])}\n"
    msg += f"تعداد فروشنده حضوری: {product['offer_count']} فروشگاه\n\n"

    if has_location:
        msg += "📍 موقعیت شما دریافت شد! در حال پیدا کردن نزدیک‌ترین فروشگاه‌ها..."
    else:
        msg += "📍 برای پیدا کردن نزدیک‌ترین فروشگاه‌ها، لطفاً لوکیشن‌تان را فعال کنید یا محله‌تان را بگویید."

    suggestions = []
    if not has_location:
        suggestions = ["سعادت‌آباد", "ونک", "تجریش", "جمهوری", "هفت‌تیر", "صادقیه"]

    cards = [{"type": "product_detail", "data": product}]

    # If we have location, immediately search for shops
    if has_location:
        shops_result = _find_shops_for_product(session, product_id)
        if shops_result.get("cards"):
            cards.extend(shops_result["cards"])
        if shops_result.get("map_markers"):
            return {
                "message": msg + "\n\n" + shops_result.get("message", ""),
                "step": "comparison",
                "cards": cards,
                "suggestions": [],
                "map_markers": shops_result["map_markers"],
                "filters": shops_result.get("filters", {}),
                "session_id": session["id"],
            }

    return {
        "message": msg,
        "step": "location",
        "cards": cards,
        "suggestions": suggestions,
        "map_markers": [],
        "filters": {},
        "session_id": session["id"],
    }


def _handle_find_shops(session: dict, product_id: str) -> dict:
    """Find shops carrying a specific product near the user."""
    if not session.get("user_lat") or not session.get("user_lon"):
        return {
            "message": "📍 لطفاً ابتدا موقعیت مکانی‌تان را مشخص کنید. می‌توانید از دکمه لوکیشن استفاده کنید یا نام محله‌تان را بگویید.",
            "step": "location",
            "cards": [],
            "suggestions": ["سعادت‌آباد", "ونک", "تجریش", "جمهوری", "هفت‌تیر"],
            "map_markers": [],
            "filters": {},
            "session_id": session["id"],
        }

    result = _find_shops_for_product(session, product_id)
    result["session_id"] = session["id"]
    return result


def _find_shops_for_product(session: dict, product_id: str, allow_widen: bool = True) -> dict:
    """Internal: Find and rank shops for a product."""
    lat = session["user_lat"]
    lon = session["user_lon"]
    bnpl_provider = session.get("bnpl_provider", "")
    radius_km = session.get("radius_km", 5.0)

    # Get offers for this product
    offers = query(
        """SELECT o.*, s.name as shop_name, s.address, s.location_label,
                  s.lat, s.lon, s.weekly_hours, s.payment_options, s.contacts,
                  s.instagram, s.website_url
           FROM offers o
           JOIN shops s ON o.shop_id = s.shop_id
           WHERE o.product_id = ? AND o.price_toman > 0
                 AND s.lat IS NOT NULL AND s.lon IS NOT NULL
           ORDER BY o.price_toman ASC""",
        (product_id,),
    )

    if not offers:
        return {
            "message": "متأسفانه فروشگاه حضوری‌ای برای این محصول در تهران پیدا نشد. 😔",
            "step": "comparison",
            "cards": [],
            "suggestions": [],
            "map_markers": [],
            "filters": {},
        }

    # Enrich with distance, hours, mall info, BNPL (deduplicated by shop)
    shops_list = []
    seen_shops = set()
    for o in offers:
        if not o.get("lat") or not o.get("lon"):
            continue
        if o["shop_id"] in seen_shops:
            continue
        seen_shops.add(o["shop_id"])

        dist = haversine_m(lat, lon, o["lat"], o["lon"])
        hours_status = check_shop_status(o.get("weekly_hours", ""))
        mall_info = parse_mall_info(o.get("address", ""))
        bnpl_providers = get_bnpl_providers(o.get("payment_options", ""))
        price_age = _price_age_info(o.get("last_price_changed_at", ""))

        # Apply radius filter server-side so results match the UI slider
        if dist > radius_km * 1000:
            continue

        # Apply BNPL filter
        if bnpl_provider and bnpl_provider not in bnpl_providers:
            continue

        mall_guide = ""
        if mall_info:
            mall_guide = generate_mall_guide(mall_info)

        shops_list.append({
            "shop_id": o["shop_id"],
            "offer_id": o["offer_id"],
            "name": o["shop_name"],
            "address": o.get("address", ""),
            "location_label": o.get("location_label", ""),
            "lat": o["lat"],
            "lon": o["lon"],
            "distance_m": round(dist),
            "distance_display": f"{dist/1000:.1f} کیلومتر" if dist >= 1000 else f"{int(dist)} متر",
            "price_toman": o["price_toman"],
            "price_display": _format_price(o["price_toman"]),
            "is_open": hours_status["is_open"],
            "open_status": hours_status["status_text"],
            "hours_detail": hours_status["detail"],
            "mall_info": mall_info,
            "mall_guide": mall_guide,
            "bnpl_providers": bnpl_providers,
            "has_bnpl": len(bnpl_providers) > 0,
            "warranty": o.get("warranty", ""),
            "seller_title": o.get("seller_title", ""),
            "price_age": price_age,
            "contacts": o.get("contacts", ""),
            "instagram": o.get("instagram", ""),
            "website_url": o.get("website_url", ""),
        })

    if not shops_list:
        # Distinguish "no shop carries this product at all" from
        # "shops exist but none match the active filters" – the latter is
        # very common when a BNPL provider is requested.
        total_offers = len({o["shop_id"] for o in offers})

        # ── Fast fallback: widen the radius before giving up ──────────
        # The user is standing on a street; telling them "nothing found"
        # is worse than showing a shop 4 km away. Widen progressively
        # (5 → 10 → 20 km) and keep the first non-empty result.
        # `allow_widen` prevents infinite recursion between the two levels.
        if not bnpl_provider and total_offers > 0 and radius_km < 20 and allow_widen:
            for wider in (10.0, 20.0):
                session["radius_km"] = wider
                retry = _find_shops_for_product(session, product_id, allow_widen=False)
                retry_shops = []
                for c in retry.get("cards", []):
                    if c.get("type") == "shop_list":
                        retry_shops = c.get("data", {}).get("shops", [])
                if retry_shops:
                    retry["message"] = (
                        f"🔎 در شعاع {radius_km:g} کیلومتر فروشگاهی پیدا نشد؛ "
                        f"با گسترش شعاع به {wider:g} کیلومتر این گزینه‌ها را پیدا کردم:\n\n"
                        + retry.get("message", "")
                    )
                    retry["message"] += (
                        f"\n\n💡 می‌توانید شعاع را به {radius_km:g} کیلومتر برگردانید."
                    )
                    return retry
            # Restore the requested radius – the fallback did not help.
            session["radius_km"] = radius_km

        if bnpl_provider and total_offers > 0:
            msg = (
                f"هیچ‌کدام از {total_offers} فروشگاهِ این محصول، گزینهٔ «{bnpl_provider}» را "
                "به‌صورت حضوری ارائه نمی‌کنند."
            )
            msg += "\n💡 پیشنهاد: فیلتر اقساطی را بردارید تا همهٔ فروشگاه‌ها را ببینید."
        elif radius_km < 10:
            msg = (
                f"هیچ فروشگاهی برای این محصول در شعاع {radius_km:g} کیلومتری شما پیدا نشد."
            )
            msg += "\n💡 پیشنهاد: شعاع جستجو را به ۵ یا ۱۰ کیلومتر افزایش دهید."
        else:
            msg = "متأسفانه فروشگاهی با شرایط مورد نظر شما پیدا نشد."
            msg += "\n💡 پیشنهاد: فیلترها را بردارید یا کالای دیگری را انتخاب کنید."

        return {
            "message": msg,
            "step": "comparison",
            "cards": [],
            "suggestions": ["نمایش بدون فیلتر اقساطی", "جستجوی محصول مشابه"]
            if bnpl_provider
            else ["جستجوی محصول مشابه"],
            "map_markers": [],
            "filters": {"bnpl_active": bool(bnpl_provider), "bnpl_provider": bnpl_provider},
            "session_id": session["id"],
        }

    # Sort by composite score: distance weight 40%, price weight 40%, open status 20%
    min_price = min(s["price_toman"] for s in shops_list) or 1
    max_dist = max(s["distance_m"] for s in shops_list) or 1

    for s in shops_list:
        price_score = 1 - (s["price_toman"] - min_price) / max(max(s2["price_toman"] for s2 in shops_list) - min_price, 1)
        dist_score = 1 - s["distance_m"] / max_dist
        open_score = 1.0 if s["is_open"] else (0.3 if s["is_open"] is None else 0.0)
        s["score"] = round(price_score * 0.35 + dist_score * 0.40 + open_score * 0.25, 3)

    shops_list.sort(key=lambda x: x["score"], reverse=True)
    shops_list = shops_list[:15]

    session["step"] = "comparison"

    # Build map markers
    markers = [
        {
            "lat": s["lat"],
            "lon": s["lon"],
            "title": f"{s['name']} - {s['price_display']}",
            "shop_id": s["shop_id"],
            "is_open": s["is_open"],
            "price": s["price_toman"],
        }
        for s in shops_list
    ]

    # Count stats
    open_count = sum(1 for s in shops_list if s["is_open"])
    bnpl_count = sum(1 for s in shops_list if s["has_bnpl"])
    nearest = shops_list[0] if shops_list else None
    cheapest = min(shops_list, key=lambda x: x["price_toman"]) if shops_list else None

    msg = f"🏪 **{len(shops_list)} فروشگاه** این محصول را دارند:\n"
    if open_count:
        msg += f"• 🟢 {open_count} فروشگاه همین الان باز است\n"
    if bnpl_count:
        msg += f"• 💳 {bnpl_count} فروشگاه خرید اقساطی دارد\n"
    if nearest:
        msg += f"• 📍 نزدیک‌ترین: {nearest['name']} ({nearest['distance_display']})\n"
    if cheapest and cheapest != nearest:
        msg += f"• 💰 ارزان‌ترین: {cheapest['name']} ({cheapest['price_display']})\n"

    msg += "\nفروشگاه مورد نظر را انتخاب کنید تا اطلاعات کامل و مسیریابی را ببینید."

    return {
        "message": msg,
        "step": "comparison",
        "cards": [{"type": "shop_list", "data": {"shops": shops_list, "product_id": product_id}}],
        "suggestions": [],
        "map_markers": markers,
        "filters": {
            "sort_options": ["امتیاز ترکیبی", "نزدیک‌ترین", "ارزان‌ترین", "فقط باز"],
            "bnpl_providers": list(set(p for s in shops_list for p in s["bnpl_providers"])),
            # The radius that was actually applied. This may be wider than the
            # one the user asked for, because of the automatic fallback
            # (5 → 10 → 20 km). The client uses it to avoid filtering the
            # server's own results out a second time.
            "radius_km": radius_km,
        },
    }


def _handle_shop_selected(session: dict, shop_id: str, product_id: str) -> dict:
    """Show detailed shop info with navigation guide."""
    shop = query_one("SELECT * FROM shops WHERE shop_id = ?", (shop_id,))
    if not shop:
        return {"message": "فروشگاه یافت نشد.", "step": "comparison", "cards": [], "suggestions": [], "map_markers": [], "filters": {}, "session_id": session["id"]}

    # Get offer for this product
    offer = query_one(
        "SELECT * FROM offers WHERE shop_id = ? AND product_id = ? AND price_toman > 0",
        (shop_id, product_id),
    )

    hours_status = check_shop_status(shop.get("weekly_hours", ""))
    mall_info = parse_mall_info(shop.get("address", ""))
    mall_guide = generate_mall_guide(mall_info) if mall_info else ""
    bnpl_providers = get_bnpl_providers(shop.get("payment_options", ""))
    price_age = _price_age_info(offer.get("last_price_changed_at", "")) if offer else {"days": -1, "label": "نامشخص", "color": "gray"}

    dist = None
    if session.get("user_lat") and session.get("user_lon") and shop.get("lat") and shop.get("lon"):
        dist = haversine_m(session["user_lat"], session["user_lon"], shop["lat"], shop["lon"])

    detail = {
        "shop_id": shop["shop_id"],
        "name": shop["name"],
        "address": shop.get("address", ""),
        "location_label": shop.get("location_label", ""),
        "lat": shop.get("lat"),
        "lon": shop.get("lon"),
        "distance_m": round(dist) if dist else None,
        "distance_display": (f"{dist/1000:.1f} کیلومتر" if dist and dist >= 1000 else f"{int(dist)} متر") if dist else "",
        "is_open": hours_status["is_open"],
        "open_status": hours_status["status_text"],
        "hours_detail": hours_status["detail"],
        "mall_info": mall_info,
        "mall_guide": mall_guide,
        "bnpl_providers": bnpl_providers,
        "has_bnpl": len(bnpl_providers) > 0,
        "price_toman": offer["price_toman"] if offer else 0,
        "price_display": _format_price(offer["price_toman"]) if offer else "نامشخص",
        "price_age": price_age,
        "warranty": offer.get("warranty", "") if offer else "",
        "seller_title": offer.get("seller_title", "") if offer else "",
        "contacts": shop.get("contacts", ""),
        "instagram": shop.get("instagram", ""),
        "website_url": shop.get("website_url", ""),
        "product_id": product_id,
    }

    msg = f"### 🏪 {shop['name']}\n\n"
    msg += f"📍 {shop.get('address', '')}\n"
    if mall_guide:
        msg += f"\n{mall_guide}\n"
    msg += f"\n{hours_status['status_text']}"
    if hours_status['detail']:
        msg += f" ({hours_status['detail']})"
    msg += f"\n💰 قیمت: {detail['price_display']}"
    msg += f"\n📅 آخرین به‌روزرسانی قیمت: {price_age['label']}"
    if detail['has_bnpl']:
        msg += f"\n💳 خرید اقساطی: {', '.join(bnpl_providers)}"
    if detail.get('warranty') and detail['warranty'] != 'null':
        msg += f"\n🛡️ گارانتی: {detail['warranty']}"

    # Warning for old prices
    if price_age.get("days", 0) > 14:
        msg += "\n\n⚠️ **توجه:** قیمت این فروشگاه بیش از ۲ هفته است که به‌روزرسانی نشده. پیشنهاد می‌کنم قبل از مراجعه، با فروشگاه تماس بگیرید."

    # Warning if shop is closed
    if hours_status["is_open"] is False:
        msg += "\n\n🔴 **این فروشگاه در حال حاضر بسته است.** می‌خواهید فروشگاه‌های جایگزین باز را ببینید؟"

    markers = []
    if shop.get("lat") and shop.get("lon"):
        markers = [{"lat": shop["lat"], "lon": shop["lon"], "title": shop["name"], "shop_id": shop["shop_id"], "is_open": hours_status["is_open"], "price": detail["price_toman"]}]

    session["step"] = "verification"

    return {
        "message": msg,
        "step": "verification",
        "cards": [{"type": "shop_detail", "data": detail}],
        "suggestions": ["فروشگاه‌های جایگزین", "استعلام قیمت و موجودی"],
        "map_markers": markers,
        "filters": {},
        "session_id": session["id"],
    }


def _handle_verify_shop(session: dict, shop_id: str, product_id: str) -> dict:
    """Verify live stock/price with a shop (simulated merchant call)."""
    import random

    shop = query_one(
        "SELECT name, contacts, weekly_hours, lat, lon FROM shops WHERE shop_id = ?",
        (shop_id,),
    )
    offer = query_one(
        "SELECT * FROM offers WHERE shop_id = ? AND product_id = ? AND price_toman > 0",
        (shop_id, product_id),
    )

    shop_name = shop["name"] if shop else "فروشگاه"
    price = offer["price_toman"] if offer else 0

    # A closed store can never be reached – that is a deterministic
    # "no_response", not a random one.
    hours_status = check_shop_status(shop.get("weekly_hours", "") if shop else "")

    if not shop or not offer:
        msg = (
            f"⏳ **عدم پاسخگویی {shop_name}**\n\n"
            "اطلاعات تماس یا آفر این کالا در ترب ثبت نشده است.\n"
            "💡 **پیشنهاد:** فروشگاه‌های جایگزین نزدیک را بررسی کنید."
        )
        return {
            "message": msg,
            "step": "verification",
            "cards": [
                {
                    "type": "verification",
                    "data": {
                        "status": "no_response",
                        "shop_id": shop_id,
                        "product_id": product_id,
                        "new_price": price,
                    },
                }
            ],
            "suggestions": ["فروشگاه‌های جایگزین", "جستجوی محصول جدید"],
            "map_markers": [],
            "filters": {},
            "session_id": session["id"],
        }

    if hours_status["is_open"] is False:
        msg = (
            f"🔴 **{shop_name} در حال حاضر بسته است**\n\n"
            f"{hours_status['detail'] or hours_status['status_text']}\n\n"
            "💡 **پیشنهاد:** فروشگاه‌های جایگزین باز در همین محدوده را ببینید."
        )
        return {
            "message": msg,
            "step": "verification",
            "cards": [
                {
                    "type": "verification",
                    "data": {
                        "status": "no_response",
                        "shop_id": shop_id,
                        "product_id": product_id,
                        "new_price": price,
                    },
                }
            ],
            "suggestions": ["فروشگاه‌های جایگزین", "جستجوی محصول جدید"],
            "map_markers": [],
            "filters": {},
            "session_id": session["id"],
        }

    # Simulate 3 possible outcomes
    scenario = random.choice(["confirmed", "price_changed", "no_response"])
    new_price = price

    if scenario == "confirmed":
        msg = f"✅ **استعلام موفق از {shop_name}:**\n\n"
        msg += f"• کالا موجود است\n"
        msg += f"• قیمت: {_format_price(price)} (تأیید شده)\n"
        msg += "• می‌توانید با خیال راحت مراجعه کنید! 🎉"
        status = "confirmed"
    elif scenario == "price_changed":
        new_price = int(price * random.uniform(0.92, 1.08))
        msg = f"⚡ **پاسخ {shop_name}:**\n\n"
        msg += f"• کالا موجود است\n"
        msg += f"• قیمت قبلی: {_format_price(price)}\n"
        msg += f"• **قیمت جدید: {_format_price(new_price)}**\n"
        diff = new_price - price
        if diff > 0:
            msg += f"• ⬆️ {_format_price(abs(diff))} گران‌تر شده"
        else:
            msg += f"• ⬇️ {_format_price(abs(diff))} ارزان‌تر شده! 🎉"
        status = "price_changed"
    else:
        msg = f"⏳ **عدم پاسخگویی {shop_name}**\n\n"
        msg += "فروشگاه در حال حاضر پاسخگو نیست.\n"
        msg += "💡 **پیشنهاد:** فروشگاه‌های جایگزین نزدیک را بررسی کنید."
        status = "no_response"

    return {
        "message": msg,
        "step": "verification",
        "cards": [{"type": "verification", "data": {"status": status, "shop_id": shop_id, "product_id": product_id, "new_price": new_price}}],
        "suggestions": ["فروشگاه‌های جایگزین", "جستجوی محصول جدید"] if status == "no_response" else ["مسیریابی تا فروشگاه", "جستجوی محصول جدید"],
        "map_markers": [],
        "filters": {},
        "session_id": session["id"],
    }


def _handle_find_alternatives(session: dict, shop_id: str, product_id: str) -> dict:
    """Find alternative shops for the same product."""
    lat = session.get("user_lat", 35.7)
    lon = session.get("user_lon", 51.4)

    alternatives = find_alternative_shops(shop_id, product_id, lat, lon, radius_km=5.0, limit=5)

    if not alternatives:
        return {
            "message": "متأسفانه فروشگاه جایگزینی در نزدیکی شما پیدا نشد. 😔",
            "step": "fallback",
            "cards": [],
            "suggestions": ["جستجوی محصول مشابه", "افزایش شعاع جستجو"],
            "map_markers": [],
            "filters": {},
            "session_id": session["id"],
        }

    # Enrich alternatives
    alt_shops = []
    for a in alternatives:
        hours_status = check_shop_status(a.get("weekly_hours", ""))
        mall_info = parse_mall_info(a.get("address", ""))
        bnpl_providers = get_bnpl_providers(a.get("payment_options", ""))
        price_age = _price_age_info(a.get("last_price_changed_at", ""))
        dist = a.get("distance_m", 0)

        alt_shops.append({
            "shop_id": a["shop_id"],
            "name": a["name"],
            "address": a.get("address", ""),
            "distance_m": dist,
            "distance_display": f"{dist/1000:.1f} کیلومتر" if dist >= 1000 else f"{int(dist)} متر",
            "price_toman": a.get("price_toman", 0),
            "price_display": _format_price(a.get("price_toman", 0)),
            "is_open": hours_status["is_open"],
            "open_status": hours_status["status_text"],
            "mall_info": mall_info,
            "mall_guide": generate_mall_guide(mall_info) if mall_info else "",
            "bnpl_providers": bnpl_providers,
            "has_bnpl": len(bnpl_providers) > 0,
            "price_age": price_age,
        })

    open_alts = [a for a in alt_shops if a["is_open"]]
    nearest = alt_shops[0] if alt_shops else None

    msg = f"🔄 **{len(alt_shops)} فروشگاه جایگزین** پیدا شد:\n\n"
    if open_alts:
        msg += f"• 🟢 {len(open_alts)} فروشگاه همین الان باز است\n"
    if nearest:
        msg += f"• 📍 نزدیک‌ترین: {nearest['name']} ({nearest['distance_display']}) - {nearest['price_display']}"
        same_mall = parse_mall_info(nearest.get("address", ""))
        if same_mall:
            msg += f"\n• 🏬 در {same_mall['mall_name']}"

    markers = [
        {"lat": a["lat"], "lon": a["lon"], "title": f"{a['name']} - {a['price_display']}", "shop_id": a["shop_id"], "is_open": a["is_open"], "price": a["price_toman"]}
        for a in alt_shops if a.get("lat") and a.get("lon")
    ]

    return {
        "message": msg,
        "step": "fallback",
        "cards": [{"type": "shop_list", "data": {"shops": alt_shops, "product_id": product_id, "is_alternative": True}}],
        "suggestions": [],
        "map_markers": markers,
        "filters": {},
        "session_id": session["id"],
    }


def _handle_compare_shops(session: dict, product_id: str) -> dict:
    """Compare all shops for a product."""
    return _handle_find_shops(session, product_id)


def _handle_bnpl_query(session: dict, intent: dict) -> dict:
    """Handle installment purchase queries."""
    session["bnpl_required"] = True
    session["bnpl_provider"] = intent.get("bnpl_provider", "")

    if session.get("selected_product"):
        return _handle_find_shops(session, session["selected_product"]["product_id"])

    provider = intent.get("bnpl_provider", "خرید اقساطی")
    msg = f"💳 فیلتر **{provider}** فعال شد.\n\nحالا بگویید دنبال چه محصولی هستید تا فروشگاه‌هایی با امکان خرید اقساطی را پیدا کنم."
    return {
        "message": msg,
        "step": "discovery",
        "cards": [],
        "suggestions": ["کفش کتونی", "گوشی موبایل", "لپ‌تاپ"],
        "map_markers": [],
        "filters": {"bnpl_active": True, "bnpl_provider": intent.get("bnpl_provider", "")},
        "session_id": session["id"],
    }


def _handle_area_search(session: dict, intent: dict) -> dict:
    """Handle when user specifies an area/location."""
    area = intent.get("area", "")
    session["user_lat"] = intent.get("lat")
    session["user_lon"] = intent.get("lon")

    if session.get("selected_product"):
        msg = f"📍 موقعیت شما: **{area}**\n\nدر حال جستجوی فروشگاه‌ها..."
        shops_result = _find_shops_for_product(session, session["selected_product"]["product_id"])
        return {
            "message": msg + "\n\n" + shops_result.get("message", ""),
            "step": shops_result.get("step", "comparison"),
            "cards": shops_result.get("cards", []),
            "suggestions": shops_result.get("suggestions", []),
            "map_markers": shops_result.get("map_markers", []),
            "filters": shops_result.get("filters", {}),
            "session_id": session["id"],
        }

    msg = f"📍 موقعیت شما: **{area}**\n\nعالیه! حالا بگویید دنبال چه محصولی هستید؟"
    return {
        "message": msg,
        "step": "location",
        "cards": [],
        "suggestions": ["کفش کتونی", "گوشی موبایل", "لپ‌تاپ", "هدفون"],
        "map_markers": [],
        "filters": {},
        "session_id": session["id"],
    }
