"""
test_llm_agent.py – Generative-UI backend tests (LLM MOCKED, no network).

Covers: ui schema validation, cards->blocks adapter, the LLM tool->block
flow with a fake client, fallback on timeout / missing key, and that the
session location context is injected into the deterministic tools.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.database import query_one
from backend.main import app
from backend.services import llm_agent
from backend.services.ui_schema import cards_to_ui_blocks, validate_ui_blocks


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def sample_product():
    row = query_one(
        """SELECT p.product_id FROM products p JOIN offers o ON o.product_id = p.product_id
           WHERE o.price_toman > 0 LIMIT 1"""
    )
    assert row, "Database has no products with offers – run ingest first"
    return row["product_id"]


# ── fake OpenAI client helpers ─────────────────────────────────

def _tool_call_msg(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        content=None,
        tool_calls=[SimpleNamespace(
            id=call_id,
            function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
        )],
    )


def _content_msg(content):
    return SimpleNamespace(content=content, tool_calls=None)


def _resp(msg):
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=None)


class _FakeClient:
    """Returns queued canned responses, recording every create() kwargs."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

        outer = self

        class _Completions:
            @staticmethod
            def create(**kwargs):
                outer.calls.append(kwargs)
                if not outer.responses:
                    raise RuntimeError("fake client out of responses")
                item = outer.responses.pop(0)
                if isinstance(item, Exception):
                    raise item
                return item

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


# ── 1) schema validation ───────────────────────────────────────

class TestUISchema:
    def test_unknown_and_malformed_blocks_dropped(self):
        raw = [
            {"type": "bogus_type", "props": {}},                      # unknown type
            "not-a-dict",                                            # not a dict
            {"type": "product_carousel", "props": {}},                # missing products
            {"type": "product_carousel", "props": {"products": []}},  # empty products
            {"type": "shop_map_list", "props": {"shops": []}},        # empty shops
            {"type": "quick_replies", "props": {"replies": []}},      # empty replies
            {"type": "quick_replies", "props": {"replies": "no"}},     # wrong type
            {"type": "quick_replies", "props": {"replies": ["نمایش ارزان‌ترین", "فروشگاه‌های نزدیک"]}},
            {"type": "verification_progress", "props": {"status": "confirmed"}},
            {"type": "verification_progress", "props": {"status": "weird"}},
            {"type": "fallback_notice", "props": {"note": "خارج از پوشش"}},
        ]
        out = validate_ui_blocks(raw)
        types = [b["type"] for b in out]
        assert types == ["quick_replies", "verification_progress", "fallback_notice"]

    def test_block_count_capped(self):
        raw = [{"type": "fallback_notice", "props": {}} for _ in range(20)]
        assert len(validate_ui_blocks(raw)) == 6  # MAX_UI_BLOCKS


# ── 2) cards -> ui adapter ─────────────────────────────────────

class TestCardsAdapter:
    def test_product_list_to_carousel(self):
        blocks = cards_to_ui_blocks([
            {"type": "product_list", "data": {"products": [{"product_id": "p1"}], "query": "کتونی"}},
        ])
        assert blocks and blocks[0]["type"] == "product_carousel"
        assert blocks[0]["props"]["products"][0]["product_id"] == "p1"

    def test_shop_list_and_verification_mapped(self):
        blocks = cards_to_ui_blocks([
            {"type": "shop_list", "data": {"shops": [{"shop_id": "s1"}], "product_id": "p1"}},
            {"type": "shop_list", "data": {"shops": [{"shop_id": "s2"}], "is_alternative": True}},
            {"type": "verification", "data": {"status": "price_changed", "new_price": 123}},
        ])
        types = [b["type"] for b in blocks]
        assert types == ["shop_map_list", "alternatives_panel", "verification_progress"]
        assert blocks[2]["props"]["status"] == "price_changed"

    def test_empty_and_invalid_cards(self):
        assert cards_to_ui_blocks([]) == []
        assert cards_to_ui_blocks([{"type": "shop_list", "data": {"shops": []}}]) == []


# ── 3) LLM tool->block flow (fake client) ───────────────────────

class TestLLMFlow:
    def test_tool_call_produces_blocks_and_cards(self, monkeypatch, sample_product):
        fake = _FakeClient([
            _resp(_tool_call_msg("search_products", {"query": "گوشی"})),
            _resp(_content_msg(json.dumps({
                "message": "این گوشی‌ها نزدیک شما موجود است.",
                "ui": [
                    {"type": "quick_replies", "props": {"replies": ["نمایش ارزان‌ترین", "فروشگاه‌های نزدیک"]}},
                    {"type": "bogus", "props": {}},               # must be dropped
                    {"type": "quick_replies", "props": {"replies": []}},  # must be dropped
                ],
            }, ensure_ascii=False))),
        ])
        monkeypatch.setattr(llm_agent, "_get_client", lambda: fake)

        result = llm_agent.handle_chat(
            message="گوشی موبایل", session_id="t-llm-flow", lat=35.695, lon=51.406,
        )
        assert result["llm_used"] is True
        # deterministic search block + cards for the current frontend
        assert any(c["type"] == "product_list" for c in result["cards"])
        carousel = next(b for b in result["ui"] if b["type"] == "product_carousel")
        assert carousel["props"]["products"]
        assert carousel["props"]["products"][0]["product_id"]  # real data, not invented
        # light blocks validated: only the good quick_replies survives
        qr = [b for b in result["ui"] if b["type"] == "quick_replies"]
        assert len(qr) == 1 and len(qr[0]["props"]["replies"]) == 2
        # suggestions mirror quick_replies for the current UI
        assert result["suggestions"] == qr[0]["props"]["replies"]
        # deterministic data headline (tests + honesty guarantee)
        assert "محصول" in result["message"] and "«گوشی»" in result["message"]
        assert "این گوشی‌ها" in result["message"]  # LLM advisory tail kept

    def test_location_context_passed_to_tools(self, monkeypatch, sample_product):
        captured = {}

        def fake_execute_tool(name, args, session):
            captured["name"] = name
            captured["session_lat"] = session.get("user_lat")
            captured["session_lon"] = session.get("user_lon")
            return {
                "payload": {"count": 0},
                "blocks": [{"type": "fallback_notice", "props": {"note": "تست"}}],
                "cards": [],
                "step": "discovery",
                "map_markers": [],
            }

        fake = _FakeClient([
            _resp(_tool_call_msg("search_products", {"query": "کتونی"})),
            _resp(_content_msg(json.dumps({"message": "پیام", "ui": []}, ensure_ascii=False))),
        ])
        monkeypatch.setattr(llm_agent, "_get_client", lambda: fake)
        monkeypatch.setattr(llm_agent, "_execute_tool", fake_execute_tool)

        llm_agent.handle_chat(
            message="کتونی", session_id="t-llm-loc", lat=35.695, lon=51.406,
        )
        assert captured["name"] == "search_products"
        assert captured["session_lat"] == 35.695   # location injected into the tool layer
        assert captured["session_lon"] == 51.406

    def test_history_trimmed_per_session(self, monkeypatch):
        fake = _FakeClient([
            _resp(_content_msg(json.dumps({"message": "باشه", "ui": []}, ensure_ascii=False))),
        ])
        monkeypatch.setattr(llm_agent, "_get_client", lambda: fake)
        llm_agent.handle_chat(message="چی بفروشم بخرم؟", session_id="t-hist", lat=None, lon=None)
        from backend.services.agent import _get_session
        session = _get_session("t-hist")
        assert 0 < len(session["llm_history"]) <= 4  # short per-session history


# ── 4) automatic fallback ───────────────────────────────────────

class TestFallback:
    def test_timeout_falls_back_to_rule_based(self, monkeypatch):
        fake = _FakeClient([TimeoutError("llm timeout")])
        monkeypatch.setattr(llm_agent, "_get_client", lambda: fake)

        result = llm_agent.handle_chat(
            message="کتونی", session_id="t-timeout", lat=35.695, lon=51.406,
        )
        assert result["llm_used"] is False
        assert result.get("llm_note") == "TimeoutError"
        # rule-based output kept intact + ui blocks present
        assert "محصول" in result["message"]
        assert any(c["type"] == "product_list" for c in result["cards"])
        assert result["ui"], "fallback must still emit ui blocks"

    def test_missing_key_falls_back(self, client):
        # conftest disables the client globally -> this exercises the
        # missing-key path end-to-end through the HTTP router.
        r = client.post("/api/chat", json={"message": "هدفون", "session_id": "t-nokey"})
        assert r.status_code == 200
        body = r.json()
        assert body["llm_used"] is False
        assert "ui" in body and body["ui"], "router response must carry ui blocks"
        assert "cards" in body  # legacy field still working

    def test_router_always_has_ui(self, client):
        r = client.post("/api/chat", json={"message": "سلام", "session_id": "t-ui-greet"})
        body = r.json()
        assert r.status_code == 200
        assert "ui" in body and isinstance(body["ui"], list)
        assert body["llm_used"] is False  # greetings never call the LLM
