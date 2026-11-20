import pytest

import config
from pipeline import sources


class Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


class Session:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, **kw):
        return Resp(self.payload)


def test_fred_parsing_skips_missing_days(monkeypatch):
    monkeypatch.setattr(config, "FRED_API_KEY", "x")
    payload = {"observations": [{"date": "2026-11-17", "value": "64.10"},
                                {"date": "2026-11-18", "value": "."},
                                {"date": "2026-11-19", "value": "65.02"}]}
    out = sources.fetch_brent(__import__("datetime").date(2026, 11, 1), Session(payload))
    assert [o.value for o in out] == [64.10, 65.02]


def test_fred_needs_key(monkeypatch):
    monkeypatch.setattr(config, "FRED_API_KEY", "")
    with pytest.raises(sources.SourceError):
        sources.fetch_brent(None)


def test_er_api_parsing():
    payload = {"result": "success", "time_last_update_unix": 1795132801, "rates": {"NGN": 1452.3}}
    [o] = sources.fetch_usdngn(session=Session(payload))
    assert o.series == "usdngn" and o.value == 1452.3


def test_er_api_error():
    with pytest.raises(sources.SourceError):
        sources.fetch_usdngn(session=Session({"result": "error"}))


def test_product_fetchers_use_their_own_series(monkeypatch):
    monkeypatch.setattr(config, "FRED_API_KEY", "x")
    payload = {"observations": [{"date": "2026-11-19", "value": "2.415"}]}
    d = __import__("datetime").date(2026, 11, 1)
    [g] = sources.fetch_gasoline(d, Session(payload))
    [x] = sources.fetch_diesel(d, Session(payload))
    assert (g.series, g.source) == ("gasoline_nyh", "FRED:DGASNYH")
    assert (x.series, x.source) == ("diesel_nyh", "FRED:DDFUELNYH")
