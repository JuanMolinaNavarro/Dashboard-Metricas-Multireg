from __future__ import annotations

from datetime import date

from helpers import api_client
from tests.conftest import DummyResponse, make_dummy_get


def test_get_json_uses_base_url(monkeypatch):
    dummy = DummyResponse({"ok": True})
    monkeypatch.setattr(api_client.requests, "get", make_dummy_get(dummy))
    result = api_client.get_json("/metrics/test", {"a": 1})
    assert result == {"ok": True}


def test_metrics_casos_atendidos(monkeypatch):
    dummy = DummyResponse({"data": [{"fecha": "2024-01-01", "total": 10}]})
    monkeypatch.setattr(api_client.requests, "get", make_dummy_get(dummy))
    result = api_client.metrics_casos_atendidos(date(2024, 1, 1), date(2024, 1, 7))
    assert "data" in result
