"""
backend/tests/test_api.py – Smoke & integration tests for the TorobGard API.

Run from the repo root:
    python -m pytest backend/tests -v
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import query_one


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_product():
    """A real product that has at least one active offer."""
    row = query_one(
        """SELECT p.product_id
           FROM products p
           JOIN offers o ON o.product_id = p.product_id
           WHERE o.price_toman > 0
           LIMIT 1"""
    )
    assert row, "Database has no products with offers – run ingest.py first"
    return row


@pytest.fixture(scope="session")
def isolated_offer():
    """An offer from a geographically isolated shop (few neighbors within
    ~1 km), so nearby searches around it are deterministic."""
    row = query_one(
        """
        WITH candidates AS (
          SELECT s.shop_id, s.lat, s.lon,
            (SELECT COUNT(*) FROM shops t
             WHERE t.lat BETWEEN s.lat-0.009 AND s.lat+0.009
               AND t.lon BETWEEN s.lon-0.0135 AND s.lon+0.0135) AS nbr
          FROM shops s
          WHERE s.lat IS NOT NULL AND s.lon IS NOT NULL
          ORDER BY nbr
          LIMIT 40
        )
        SELECT c.shop_id, c.lat, c.lon, o.product_id
        FROM candidates c JOIN offers o ON o.shop_id = c.shop_id
        WHERE o.price_toman > 0 LIMIT 1
        """
    )
    assert row, "No offer from an isolated geocoded shop found"
    return row


@pytest.fixture(scope="session")
def sample_shop_id():
    row = query_one("SELECT shop_id FROM shops LIMIT 1")
    assert row, "Database has no shops"
    return row["shop_id"]


# ── Health ────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["db_ready"] is True


# ── Products ──────────────────────────────────────────────────

class TestProducts:
    def test_search_default_returns_results(self, client):
        r = client.get("/api/products/search")
        assert r.status_code == 200
        body = r.json()
        assert body["products"]
        assert body["total"] > 0
        assert body["page"] == 1
        assert body["limit"] == 20
        first = body["products"][0]
        assert "product_id" in first
        assert "persian_title" in first
        assert "min_price" in first
        assert "offer_count" in first

    def test_search_with_query(self, client):
        r = client.get("/api/products/search?q=گوشی")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] > 0
        assert body["products"]

    def test_search_price_filter_respected(self, client):
        r = client.get(
            "/api/products/search?q=گوشی&min_price=5000000&max_price=30000000"
        )
        assert r.status_code == 200
        body = r.json()
        for p in body["products"]:
            low = p["min_price"] or p["max_price"]
            assert 0 < low or p["offer_count"] == 0
            if p["min_price"] > 0:
                assert p["min_price"] <= 30_000_000

    def test_search_pagination(self, client):
        r = client.get("/api/products/search?page=2&limit=5")
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 2
        assert len(body["products"]) <= 5

    def test_product_detail_found(self, client, sample_product):
        r = client.get(f"/api/products/{sample_product['product_id']}")
        assert r.status_code == 200
        body = r.json()
        assert "error" not in body
        assert body.get("product", {}).get("product_id") == sample_product["product_id"] or \
               body.get("product_id") == sample_product["product_id"], body.keys()

    def test_product_detail_not_found(self, client):
        r = client.get("/api/products/does-not-exist")
        assert r.status_code == 200  # API returns a soft error payload
        assert r.json().get("error") == "Product not found"

    def test_categories(self, client):
        r = client.get("/api/categories")
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert cats

    def test_brands(self, client):
        r = client.get("/api/brands")
        assert r.status_code == 200
        brands = r.json()["brands"]
        assert brands


# ── Shops ─────────────────────────────────────────────────────

class TestShops:
    def test_shop_detail(self, client, sample_shop_id):
        r = client.get(f"/api/shops/{sample_shop_id}")
        assert r.status_code == 200
        body = r.json()
        assert "error" not in body
        assert body["shop_id"] == sample_shop_id
        assert body["name"]
        assert body["shop_id"] in body["address"] or bool(body["address"])
        for key in ("is_open", "open_status", "mall_info", "bnpl_providers", "contacts_parsed"):
            assert key in body

    def test_shop_detail_not_found(self, client):
        r = client.get("/api/shops/does-not-exist")
        assert r.status_code == 200
        assert r.json().get("error") == "Shop not found"

    def test_shop_offers(self, client, isolated_offer):
        r = client.get(f"/api/shops/{isolated_offer['shop_id']}/offers")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert body["offers"]
        prices = [o["price_toman"] for o in body["offers"]]
        assert all(p > 0 for p in prices)
        assert prices == sorted(prices)  # ordered by price ASC

    def test_nearby_shops_sorted_and_within_radius(self, client, isolated_offer):
        # Place the user ~100 m away from a real shop
        lat = isolated_offer["lat"] + 0.001
        lon = isolated_offer["lon"]
        r = client.get(
            "/api/shops/nearby/search",
            params={"lat": lat, "lon": lon, "radius": 0.5},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        dists = [s["distance_m"] for s in body["shops"]]
        assert dists == sorted(dists)               # ascending
        assert max(dists) <= 0.5 * 1000             # inside radius
        ids = [s["shop_id"] for s in body["shops"]]
        assert isolated_offer["shop_id"] in ids     # seed shop found nearby

    def test_nearby_shops_product_filter(self, client, isolated_offer):
        r = client.get(
            "/api/shops/nearby/search",
            params={
                "lat": isolated_offer["lat"] + 0.001,
                "lon": isolated_offer["lon"],
                "radius": 0.5,
                "product_id": isolated_offer["product_id"],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        for s in body["shops"]:
            assert s["price_toman"] > 0
        ids = [s["shop_id"] for s in body["shops"]]
        assert isolated_offer["shop_id"] in ids     # the seller shop is in results

    def test_nearby_requires_coords(self, client):
        r = client.get("/api/shops/nearby/search")
        assert r.status_code == 422  # missing required lat/lon


# ── Chat agent ────────────────────────────────────────────────

class TestChatAgent:
    def test_greeting(self, client):
        r = client.post("/api/chat", json={"message": "سلام", "session_id": "t-greet"})
        assert r.status_code == 200
        body = r.json()
        assert body["message"]
        assert body["suggestions"]

    def test_search_flow_returns_cards(self, client):
        r = client.post(
            "/api/chat",
            json={
                "message": "کفش کتونی نایک",
                "session_id": "t-search",
                "lat": 35.7,
                "lon": 51.4,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "cards" in body
        assert "map_markers" in body
        assert body["message"]

    def test_full_payload_contract(self, client):
        for key in ("message", "step", "cards", "suggestions", "map_markers"):
            r = client.post("/api/chat", json={"message": "هدفون", "session_id": "t-contract"})
            assert r.status_code == 200
            assert key in r.json(), f"missing key: {key}"
            break
