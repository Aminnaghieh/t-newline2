"""
ui_schema.py – Server-side contract for Generative UI blocks.

The chat response may carry `ui`: a list of typed blocks rendered by the
frontend component registry. Everything is validated here – unknown or
malformed blocks are DROPPED, never trusted. Block types are whitelisted;
the data inside `props` comes exclusively from deterministic backend tools,
never from the LLM.
"""

from typing import Any

from pydantic import BaseModel, Field
from typing import Literal

# Actively emitted blocks
EMITTED_TYPES = (
    "product_carousel",     # horizontal list of product cards
    "shop_map_list",        # shop list + map markers for a product
    "filter_chips",         # active filter chips (budget/radius/BNPL/open-now)
    "quick_replies",        # suggested next user actions (text chips)
    "verification_progress",# live verify outcome for one shop
    "fallback_notice",      # honest notice (out of coverage / no shops ...)
)
# Whitelisted for the next frontend phases
RESERVED_TYPES = (
    "compare_table",        # side-by-side shop comparison
    "alternatives_panel",   # alternative shops when a shop is closed/unresponsive
    "model_advisor_choices",# "which model should I buy?" choice cards
)

BLOCK_TYPES = frozenset(EMITTED_TYPES + RESERVED_TYPES)

MAX_UI_BLOCKS = 6
QUICK_REPLY_MAX = 6
VERIFICATION_STATUSES = frozenset({"confirmed", "price_changed", "no_response"})


class UIBlock(BaseModel):
    """A single Generative-UI block. `props` is a free-but-validated dict."""
    type: Literal[
        "product_carousel", "shop_map_list", "filter_chips", "quick_replies",
        "verification_progress", "fallback_notice", "compare_table",
        "alternatives_panel", "model_advisor_choices",
    ]
    props: dict = Field(default_factory=dict)


def _valid_product_carousel(props: dict) -> bool:
    return isinstance(props.get("products"), list) and len(props["products"]) > 0


def _valid_shop_map_list(props: dict) -> bool:
    return isinstance(props.get("shops"), list) and len(props["shops"]) > 0


def _valid_quick_replies(props: dict) -> bool:
    replies = props.get("replies")
    return (
        isinstance(replies, list)
        and 0 < len(replies) <= QUICK_REPLY_MAX
        and all(isinstance(r, str) and r.strip() for r in replies)
    )


def _valid_filter_chips(props: dict) -> bool:
    chips = props.get("chips")
    return chips is None or (isinstance(chips, list) and len(chips) <= 10)


def _valid_verification_progress(props: dict) -> bool:
    return props.get("status") in VERIFICATION_STATUSES


_VALIDATORS = {
    "product_carousel": _valid_product_carousel,
    "shop_map_list": _valid_shop_map_list,
    "compare_table": _valid_shop_map_list,
    "alternatives_panel": _valid_shop_map_list,
    "quick_replies": _valid_quick_replies,
    "filter_chips": _valid_filter_chips,
    "verification_progress": _valid_verification_progress,
    "fallback_notice": lambda props: True,
    "model_advisor_choices": lambda props: isinstance(props.get("choices"), list)
    and len(props["choices"]) > 0,
}


def validate_ui_blocks(raw: Any) -> list[dict]:
    """Validate a candidate `ui` list. Unknown types, malformed entries and
    anything beyond MAX_UI_BLOCKS is silently dropped (never trusted)."""
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        btype = item.get("type")
        if btype not in BLOCK_TYPES:
            continue
        props = item.get("props")
        if props is None:
            props = {}
        if not isinstance(props, dict):
            continue
        try:
            block = UIBlock(type=btype, props=props)
        except Exception:
            continue
        if not _VALIDATORS[btype](block.props):
            continue
        out.append({"type": block.type, "props": block.props})
        if len(out) >= MAX_UI_BLOCKS:
            break
    return out


# ─── Adapter: existing rule-based `cards` -> ui blocks ──────────────
# The rule-based agent keeps producing its classic `cards`; this adapter
# projects them into the Generative-UI contract so the fallback path and
# the LLM path speak the same language.

def cards_to_ui_blocks(cards: list[dict] | None) -> list[dict]:
    """Deterministically map the legacy card list to validated ui blocks."""
    if not cards:
        return []
    out: list[dict] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        ctype = card.get("type")
        data = card.get("data") or {}
        if ctype == "product_list":
            products = data.get("products") or []
            if products:
                out.append({
                    "type": "product_carousel",
                    "props": {"products": products, "query": data.get("query", "")},
                })
        elif ctype == "shop_list":
            shops = data.get("shops") or []
            if shops:
                block_type = "alternatives_panel" if data.get("is_alternative") else "shop_map_list"
                out.append({
                    "type": block_type,
                    "props": {"shops": shops, "product_id": data.get("product_id", "")},
                })
        elif ctype == "verification":
            out.append({
                "type": "verification_progress",
                "props": {
                    "status": data.get("status", "no_response"),
                    "shop_id": data.get("shop_id", ""),
                    "product_id": data.get("product_id", ""),
                    "new_price": data.get("new_price", 0),
                },
            })
        elif ctype == "product_detail":
            product = data if data.get("product_id") else {}
            if product:
                out.append({
                    "type": "model_advisor_choices",
                    "props": {"choices": [product]},
                })
    return validate_ui_blocks(out)


def quick_replies_of(ui: list[dict]) -> list[str]:
    """Extract the first quick_replies block (used for legacy suggestions)."""
    for block in ui:
        if block.get("type") == "quick_replies":
            return list(block.get("props", {}).get("replies", []))
    return []
