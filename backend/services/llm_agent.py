"""
llm_agent.py – LLM-orchestrated agent for Generative UI.

Contract:
- The LLM (BoxAPI, OpenAI-compatible) chooses WHICH deterministic tools to
  call and writes a short Persian message (plus optional light blocks:
  quick_replies / filter_chips / fallback_notice).
- The server converts every tool result into its UI block deterministically.
- The LLM never invents prices, distances, hours or availability – all data
  comes from the existing deterministic services.
- Any failure (missing key, client error, ~8s timeout, malformed output)
  falls back to the existing rule-based agent, whose `cards` output is
  adapted into ui blocks – the demo can never break.
"""

import json
import os

from dotenv import load_dotenv

from backend.services import agent
from backend.services.search import search_products
from backend.services.ui_schema import (
    cards_to_ui_blocks,
    quick_replies_of,
    validate_ui_blocks,
)

# Pick up .env when the server runs locally (no-op when env vars are
# provided by the platform, e.g. Docker/Liara).
load_dotenv()

LLM_TIMEOUT_S = 8.0
MAX_TOOL_ITERATIONS = 2
MAX_TOOLS_PER_TURN = 3
MAX_HISTORY = 4            # short per-session history (2 user/assistant turns)
LLM_MAX_COMPLETION_TOKENS = 600

_client = None


def _get_client():
    """Lazily build the OpenAI client from env.

    Returns None when LLM_API_KEY is missing -> the caller falls back to
    the rule-based agent. Tests monkeypatch this seam to stay offline.
    """
    global _client
    if _client is None:
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            return None
        from openai import OpenAI
        _client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL") or None,
            api_key=api_key,
            timeout=LLM_TIMEOUT_S,
            max_retries=0,
        )
    return _client


def _model() -> str:
    return os.getenv("LLM_MODEL") or "gpt-5.4-mini"


SYSTEM_PROMPT = """تو «ترب‌گرد» هستی، دستیار هوشمند خرید حضوری در پاساژها و بازارهای تهران.

قوانین:
۱) فقط فارسی، خودمانی و کوتاه جواب بده (حداکثر ۳ جمله).
۲) برای هر داده‌ای (قیمت، فاصله، ساعت کاری، موجودی) فقط از ابزارها استفاده کن؛ هرگز عدد یا ادعایی از خودت نساز.
۳) موقعیت کاربر به‌صورت خودکار در ابزارها تزریق می‌شود؛ مختصات نخواه.
۴) عبارت کامل کاربر را در پاسخ نقل نکن.
۵) اگر ابزاری داده برگرداند، آن را در ui تکرار نکن؛ سرور خودش بلوک داده را می‌سازد.
۶) در پایان فقط JSON معتبر با این ساختار برگردان:
{"message": "<متن کوتاه فارسی>", "ui": [{"type": "...", "props": {...}}]}
بلوک‌های مجاز برای تو فقط: quick_replies، filter_chips، fallback_notice.
برای quick_replies حداکثر ۳ گزینه کوتاه فارسی بده (مثل «نمایش ارزان‌ترین» یا «فروشگاه‌های نزدیک»).
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "جستجوی محصول در دیتابیس ترب؛ قیمت‌ها فقط از همین ابزار می‌آید",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "عبارت جستجو مثل: کتونی"},
                    "max_price": {"type": "integer", "description": "سقف قیمت به تومان (اختیاری)"},
                    "radius_km": {"type": "number", "description": "شعاع جستجوی فروشگاه نزدیک (اختیاری)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_shops_for_product",
            "description": "یافتن فروشگاه‌های حضوری نزدیک کاربر برای یک محصول مشخص",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_shop",
            "description": "استعلام زنده قیمت و موجودی از یک فروشگاه",
            "parameters": {
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string"},
                    "product_id": {"type": "string"},
                },
                "required": ["shop_id", "product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_alternatives",
            "description": "پیشنهاد فروشگاه‌های جایگزین وقتی فروشگاهی بسته یا بی‌پاسخ است",
            "parameters": {
                "type": "object",
                "properties": {
                    "shop_id": {"type": "string"},
                    "product_id": {"type": "string"},
                },
                "required": ["shop_id", "product_id"],
            },
        },
    },
]


# ─── Deterministic tools ─────────────────────────────────────
# Each executor returns a dict: {payload, blocks, cards, step, map_markers}
# `payload` is the trimmed JSON handed back to the LLM; `blocks`/`cards`
# are the deterministic UI projections of the same data.


def _product_card_data(p: dict) -> dict:
    """Same card shape the rule-based agent emits (frontend compatibility)."""
    return {
        "product_id": p["product_id"],
        "persian_title": p["persian_title"],
        "brand_name": p.get("brand_name", ""),
        "category_name": p.get("category_name", ""),
        "image_url": p.get("image_url", ""),
        "min_price": p.get("min_price", 0),
        "max_price": p.get("max_price", 0),
        "min_price_display": agent._format_price(p.get("min_price", 0)),
        "max_price_display": agent._format_price(p.get("max_price", 0)),
        "offer_count": p.get("offer_count", 0),
        "specs_summary": p.get("specs_summary", ""),
        "nearby_shops_count": p.get("nearby_shops_count", 0),
        "min_price_nearby": p.get("min_price_nearby", 0),
        "nearest_distance_m": p.get("nearest_distance_m"),
        "in_radius": bool(p.get("in_radius", True)),
    }


def _brief_product(p: dict) -> dict:
    return {
        "product_id": p["product_id"],
        "title": p.get("persian_title", ""),
        "min_price": p.get("min_price", 0),
        "nearby_shops_count": p.get("nearby_shops_count", p.get("offer_count", 0)),
        "nearest_distance_m": p.get("nearest_distance_m"),
    }


def _tool_search_products(args: dict, session: dict) -> dict:
    q = str(args.get("query") or "").strip()
    if not q:
        q = args.get("q") or "کفش کتونی"
    max_price = int(args.get("max_price") or session.get("budget_max") or 0)
    lat, lon = session.get("user_lat"), session.get("user_lon")
    radius_km = float(args.get("radius_km") or session.get("radius_km", agent.DEFAULT_RADIUS_KM))

    products = search_products(
        q=q, min_price=0, max_price=max_price, limit=12,
        lat=lat, lon=lon, radius_km=radius_km, sort="distance",
    )
    cards_data = [_product_card_data(p) for p in products]

    blocks = []
    if cards_data:
        blocks.append({
            "type": "product_carousel",
            "props": {"products": cards_data, "query": q},
        })

    return {
        "payload": {
            "query": q,
            "count": len(cards_data),
            "products": [_brief_product(p) for p in cards_data[:8]],
        },
        "blocks": blocks,
        "cards": ([{"type": "product_list", "data": {"products": cards_data, "query": q}}]
                  if cards_data else []),
        "step": "discovery",
        "map_markers": [],
    }


def _shops_from_result(result: dict) -> list[dict]:
    for card in result.get("cards", []):
        if card.get("type") == "shop_list":
            return card.get("data", {}).get("shops", [])
    return []


def _tool_find_shops(args: dict, session: dict) -> dict:
    product_id = str(args.get("product_id") or "")
    if not product_id:
        return {"payload": {"error": "product_id لازم است"}, "blocks": [], "cards": [],
                "step": "comparison", "map_markers": []}

    result = agent._find_shops_for_product(session, product_id)
    shops = _shops_from_result(result)

    blocks = []
    if shops:
        blocks.append({
            "type": "shop_map_list",
            "props": {"shops": shops, "product_id": product_id},
        })

    brief_shops = [
        {
            "shop_id": s.get("shop_id"),
            "name": s.get("name"),
            "distance_m": s.get("distance_m"),
            "price_toman": s.get("price_toman", 0),
            "is_open": s.get("is_open"),
            "open_status": s.get("open_status", ""),
        }
        for s in shops[:8]
    ]
    return {
        "payload": {"count": len(shops), "shops": brief_shops},
        "blocks": blocks,
        "cards": result.get("cards", []),
        "message": result.get("message", ""),
        "step": result.get("step", "comparison"),
        "map_markers": result.get("map_markers", []),
    }


def _tool_verify_shop(args: dict, session: dict) -> dict:
    shop_id = str(args.get("shop_id") or "")
    product_id = str(args.get("product_id") or "")
    result = agent._handle_verify_shop(session, shop_id, product_id)

    status, new_price = "no_response", 0
    for card in result.get("cards", []):
        if card.get("type") == "verification":
            status = card.get("data", {}).get("status", "no_response")
            new_price = card.get("data", {}).get("new_price", 0)

    blocks = [{
        "type": "verification_progress",
        "props": {
            "status": status,
            "shop_id": shop_id,
            "product_id": product_id,
            "new_price": new_price,
        },
    }]
    return {
        "payload": {"status": status, "new_price": new_price},
        "blocks": blocks,
        "cards": result.get("cards", []),
        "message": result.get("message", ""),
        "step": result.get("step", "verification"),
        "map_markers": [],
    }


def _tool_find_alternatives(args: dict, session: dict) -> dict:
    shop_id = str(args.get("shop_id") or "")
    product_id = str(args.get("product_id") or "")
    result = agent._handle_find_alternatives(session, shop_id, product_id)
    shops = _shops_from_result(result)

    blocks = []
    if shops:
        blocks.append({
            "type": "alternatives_panel",
            "props": {"shops": shops, "product_id": product_id},
        })

    return {
        "payload": {"count": len(shops), "shops": [
            {"shop_id": s.get("shop_id"), "name": s.get("name"),
             "distance_m": s.get("distance_m"), "price_toman": s.get("price_toman", 0)}
            for s in shops[:5]
        ]},
        "blocks": blocks,
        "cards": result.get("cards", []),
        "message": result.get("message", ""),
        "step": result.get("step", "fallback"),
        "map_markers": result.get("map_markers", []),
    }


_TOOL_EXECUTORS = {
    "search_products": _tool_search_products,
    "find_shops_for_product": _tool_find_shops,
    "verify_shop": _tool_verify_shop,
    "find_alternatives": _tool_find_alternatives,
}


def _execute_tool(name: str, args: dict, session: dict) -> dict:
    """Deterministic tool dispatch. Unknown tools -> explicit empty payload."""
    executor = _TOOL_EXECUTORS.get(name)
    if executor is None:
        return {"payload": {"error": f"ابزار ناشناخته: {name}"},
                "blocks": [], "cards": [], "step": "fallback", "map_markers": []}
    return executor(args, session)


# ─── Main entry point ─────────────────────────────────────────

def handle_chat(message: str = "", session_id: str = "", lat: float = None,
                lon: float = None, context: dict = None) -> dict:
    """Single chat entry point: LLM-orchestrated with rule-based fallback.

    Always returns a dict containing the legacy fields (message, step,
    cards, suggestions, map_markers, filters, session_id) plus the new
    `ui` block list and an `llm_used` flag.
    """
    session = agent._get_session(session_id)
    sid = session["id"]

    # Location bookkeeping (same semantics as agent.process_message):
    # reset the (possibly auto-expanded) radius when the position changes.
    if lat and lon:
        if (lat, lon) != (session.get("user_lat"), session.get("user_lon")):
            session["radius_km"] = agent.DEFAULT_RADIUS_KM
        session["user_lat"], session["user_lon"] = lat, lon

    # Deterministic UI actions (button clicks) never need the LLM.
    if context:
        result = agent.process_message(message, sid, lat, lon, context)
        return _with_ui(result, llm_used=False)

    text = (message or "").strip()
    if not text:
        result = agent.process_message(message, sid, lat, lon, context)
        return _with_ui(result, llm_used=False)

    intent = agent._detect_intent(text)
    if intent.get("type") == "greeting":
        result = agent.process_message(text, sid, lat, lon)
        return _with_ui(result, llm_used=False)

    client = _get_client()
    if client is None:
        result = agent.process_message(text, sid, lat, lon)
        return _with_ui(result, llm_used=False, note="missing_key")

    try:
        result = _llm_flow(client, session, text, intent)
        return _with_ui(result, llm_used=True)
    except Exception as exc:  # timeout, API error, malformed output, ...
        result = agent.process_message(text, sid, lat, lon)
        return _with_ui(result, llm_used=False, note=type(exc).__name__)


def _llm_flow(client, session: dict, text: str, intent: dict) -> dict:
    # Session updates from the parsed intent (mirrors agent.process_message).
    if intent.get("budget"):
        session["budget_max"] = intent["budget"]
    if intent.get("wants_bnpl"):
        session["bnpl_required"] = True
        session["bnpl_provider"] = intent.get("bnpl_provider", "")
    if intent.get("lat") and intent.get("lon"):
        if (intent["lat"], intent["lon"]) != (session.get("user_lat"), session.get("user_lon")):
            session["radius_km"] = agent.DEFAULT_RADIUS_KM
        session["user_lat"], session["user_lon"] = intent["lat"], intent["lon"]
    session.setdefault("llm_history", [])

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + list(session["llm_history"][-MAX_HISTORY:])
        + [{"role": "user", "content": text}]
    )

    # ── tool loop (max 2 iterations, JSON-capable) ─────────────
    # Every call advertises the tools AND requests strict JSON, so the
    # model's tool-free answer doubles as the final turn (BoxAPI accepts
    # tools + response_format together – verified in the smoke test).
    blocks: list[dict] = []
    cards: list[dict] = []
    map_markers: list[dict] = []
    step = "discovery"
    search_ran: dict | None = None
    tool_message = ""
    tool_messages = 0
    final_parsed: dict | None = None

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = client.chat.completions.create(
            model=_model(),
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            response_format={"type": "json_object"},
            max_completion_tokens=LLM_MAX_COMPLETION_TOKENS,
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            messages.append({"role": "assistant", "content": msg.content or ""})
            raw = msg.content or ""
            try:
                final_parsed = json.loads(raw)
                if not isinstance(final_parsed, dict):
                    raise ValueError("not a dict")
            except Exception:
                raise RuntimeError("invalid_final_json")
            break

        messages.append(msg)
        for tc in tool_calls[:MAX_TOOLS_PER_TURN]:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            outcome = _execute_tool(tc.function.name, args, session)
            tool_messages += 1
            if tc.function.name == "search_products":
                search_ran = outcome["payload"]
            if outcome.get("message"):
                tool_message = outcome["message"]
            blocks.extend(outcome["blocks"])
            cards.extend(outcome["cards"])
            map_markers.extend(outcome.get("map_markers", []))
            if outcome.get("step"):
                step = outcome["step"]
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(outcome["payload"], ensure_ascii=False, default=str)[:4000],
            })

    if final_parsed is None:
        # Tool budget exhausted without a final answer -> one last JSON-only call.
        final = client.chat.completions.create(
            model=_model(),
            messages=messages,
            response_format={"type": "json_object"},
            max_completion_tokens=LLM_MAX_COMPLETION_TOKENS,
        )
        try:
            final_parsed = json.loads(final.choices[0].message.content or "")
            if not isinstance(final_parsed, dict):
                raise ValueError("not a dict")
        except Exception:
            raise RuntimeError("invalid_final_json")

    llm_text = str(final_parsed.get("message") or "").strip()
    llm_blocks = validate_ui_blocks(final_parsed.get("ui") or [])

    # Anti-echo guard: never let the LLM quote the user's own sentence.
    probe = text.strip()[:15]
    if probe and probe in llm_text:
        llm_text = ""

    # ── message: deterministic data headline + LLM advisory tail ──
    base_message = ""
    if search_ran is not None:
        q = search_ran.get("query", "")
        n = int(search_ran.get("count") or 0)
        budget_text = ""
        if session.get("budget_max"):
            budget_text = f" (بودجه: {agent._format_price(session['budget_max'])})"
        if n > 0:
            base_message = (
                f"**{n} محصول** برای «{q}»{budget_text} پیدا شد.\n\n"
                "محصول مورد نظرتان را انتخاب کنید تا فروشگاه‌های حضوری نزدیک شما را پیدا کنم. 🏪"
            )
        else:
            base_message = f"متأسفانه محصولی با عنوان «{q}»{budget_text} پیدا نشد. لطفاً عبارت دیگری را امتحان کنید."
    elif tool_message:
        base_message = tool_message

    message = base_message + (("\n\n" + llm_text) if llm_text else "")
    if not message.strip():
        raise RuntimeError("empty_message")

    ui = validate_ui_blocks(blocks) + llm_blocks
    suggestions = quick_replies_of(ui)

    # short per-session history for the next turn
    session["llm_history"].append({"role": "user", "content": text})
    session["llm_history"].append({"role": "assistant", "content": message})
    session["llm_history"] = session["llm_history"][-MAX_HISTORY:]

    return {
        "message": message,
        "step": step,
        "cards": cards,
        "ui": ui,
        "suggestions": suggestions,
        "map_markers": map_markers,
        "filters": {},
        "session_id": session["id"],
    }


def _with_ui(result: dict, llm_used: bool, note: str = "") -> dict:
    """Guarantee the ui contract on every path (LLM or rule-based)."""
    if not isinstance(result, dict):
        result = {"message": "خطای غیرمنتظره", "step": "fallback", "cards": [],
                  "suggestions": [], "map_markers": [], "filters": {}}
    if "ui" not in result or not result.get("ui"):
        result["ui"] = cards_to_ui_blocks(result.get("cards", []))
        if result.get("suggestions") and not quick_replies_of(result["ui"]):
            replies = [s for s in result["suggestions"] if isinstance(s, str)][:6]
            if replies:
                result["ui"].append({"type": "quick_replies", "props": {"replies": replies}})
    result["llm_used"] = llm_used
    if note:
        result["llm_note"] = note
    return result
