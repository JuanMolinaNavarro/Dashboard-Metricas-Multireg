from __future__ import annotations

import types

import pytest


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self):
        return self._payload


@pytest.fixture()
def dummy_response():
    return DummyResponse({"ok": True})


def make_dummy_get(dummy_response):
    def _get(url, params=None, timeout=30):
        return dummy_response

    return _get
