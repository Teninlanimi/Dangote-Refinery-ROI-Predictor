import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from pipeline.sources import Observation  # noqa: E402


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    if os.getenv("TEST_DATABASE_URL"):
        url = os.environ["TEST_DATABASE_URL"]
        monkeypatch.setattr(config, "DATABASE_URL", url)
        from pipeline import db
        eng = db.get_engine(url)
        db.metadata.drop_all(eng)
        db.metadata.create_all(eng)
        return url
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(config, "DATABASE_URL", url)
    return url


def flat_series(series, price, start=date(2026, 1, 1), end=date(2026, 11, 19)):
    """Weekday prices from start to end, flat at `price`."""
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(Observation(series, d, price, "test"))
        d += timedelta(days=1)
    return out


def brent_series(start=date(2026, 1, 1), end=date(2026, 11, 19), price=70.0):
    return flat_series("brent_usd", price, start, end)


# Flat test prices: Brent $70/bbl, petrol $2.30/gal, diesel $2.50/gal
# -> 3-2-1 crack = (2 x 96.6 + 105 - 3 x 70) / 3 = $29.40/bbl


@pytest.fixture
def fake_fetchers():
    def brent(since):
        return [o for o in brent_series() if o.observed_on >= since]

    def fx(since=None):
        return [Observation("usdngn", date(2026, 11, 19), 1450.0, "test")]

    def gasoline(since):
        return [o for o in flat_series("gasoline_nyh", 2.30) if o.observed_on >= since]

    def diesel(since):
        return [o for o in flat_series("diesel_nyh", 2.50) if o.observed_on >= since]

    return {"brent_usd": brent, "gasoline_nyh": gasoline, "diesel_nyh": diesel, "usdngn": fx}


@pytest.fixture(autouse=True)
def _reset_usage_limits():
    """Each test starts with fresh usage-limit counters."""
    if "app" in sys.modules:
        sys.modules["app"].limiter.reset()
    yield
