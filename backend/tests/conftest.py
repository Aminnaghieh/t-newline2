"""
conftest.py – shared pytest fixtures for the backend suite.

The whole suite runs with the LLM client DISABLED (the rule-based
fallback path is exercised instead): no network, no cost, deterministic
results – even though a real .env key may exist on the machine.
Individual tests that need a fake LLM monkeypatch `llm_agent._get_client`
after this autouse fixture; the later patch wins.
"""

import pytest

from backend.services import llm_agent


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setattr(llm_agent, "_get_client", lambda: None)
    yield
