"""
test_security.py – Security & hardening verification test suite for TorobGard.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_security_headers_present():
    """Verify OWASP recommended security headers on all responses."""
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "strict-origin-when-cross-origin" in headers.get("referrer-policy", "")
    assert "default-src 'self'" in headers.get("content-security-policy", "")


def test_directory_traversal_prevention():
    """Ensure path traversal payloads cannot read arbitrary files."""
    # Attempting to break out of static directory
    res1 = client.get("/../../backend/database.py")
    # Must either return 200 with index.html (SPA fallback) or 404, but NEVER Python code
    assert res1.status_code in (200, 404)
    assert b"import sqlite3" not in res1.content

    res2 = client.get("/..%2F..%2F.env")
    assert res2.status_code in (200, 404)


def test_input_validation_coordinates():
    """Ensure out-of-range latitude/longitude are rejected with 422."""
    res = client.get("/api/shops/nearby/search?lat=999.0&lon=51.0")
    assert res.status_code == 422


def test_fts5_syntax_injection_safe():
    """Ensure malicious or malformed FTS syntax does not cause 500 crashes."""
    malicious_queries = [
        '"""',
        'OR OR OR',
        'NEAR(1, 2)',
        '* * *',
        'کفش" OR 1=1 --',
        '\' OR \'1\'=\'1',
    ]
    for q in malicious_queries:
        res = client.get(f"/api/products/search?q={q}")
        assert res.status_code == 200, f"Failed on query: {q}"


def test_chat_payload_length_limit():
    """Ensure excessively long chat messages are rejected."""
    huge_message = "A" * 1500
    res = client.post("/api/chat", json={"message": huge_message})
    assert res.status_code == 422
