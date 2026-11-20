from datetime import date

from pipeline import db, ingest, market
from pipeline.sources import Observation
import model
from conftest import flat_series

TODAY = date(2026, 11, 20)


def test_321_formula():
    # petrol $2.30/gal = $96.60/bbl, diesel $2.50/gal = $105/bbl
    assert abs(market.crack_321(70, 2.30, 2.50) - 29.4) < 1e-9


def test_margin_shift_behaves_like_a_refinery():
    assert model.crack_margin_shift(1.0, 1.0) == 0.0          # nothing changed
    assert model.crack_margin_shift(None, 1.3) == 0.0         # no spread data -> no shift
    assert model.crack_margin_shift(1.0, 1.2) < 0             # dearer crude, same spread: margin % falls
    assert model.crack_margin_shift(1.2, 1.0) > 0             # wider spread: margin rises
    assert model.crack_margin_shift(0.1, 1.0) == -model.MAX_MARGIN_SHIFT   # capped


def test_dearer_crude_with_flat_spread_leaves_profit_roughly_flat():
    base = model.SCENARIOS["base"]
    shift = model.crack_margin_shift(1.0, 1.2)
    live = model.with_market(base, 1.2, shift)
    profit_before = base["revenue_usd_bn"] * base["net_margin"]
    profit_after = live["revenue_usd_bn"] * live["net_margin"]
    # revenue-only scaling would add 20%; with the spread it stays within ~1%
    assert abs(profit_after / profit_before - 1) < 0.02


def test_spread_needs_all_three_prices_on_same_day(db_url, fake_fetchers):
    del fake_fetchers["diesel_nyh"]
    ingest.run(db_url, fake_fetchers, TODAY)
    snap = market.snapshot(db.get_engine(db_url), TODAY)
    assert snap["crack"] is None and snap["available"]["crack"] is False


def test_narrower_spread_lowers_live_roi(db_url, fake_fetchers):
    import app as app_module
    # H1 2026 at $2.30 petrol; from July petrol drops to $2.10 -> narrower spread
    def gasoline(since):
        rows = flat_series("gasoline_nyh", 2.30, end=date(2026, 6, 30)) + \
            flat_series("gasoline_nyh", 2.10, start=date(2026, 7, 1))
        return [o for o in rows if o.observed_on >= since]
    fake_fetchers["gasoline_nyh"] = gasoline
    ingest.run(db_url, fake_fetchers, TODAY)
    c = app_module.app.test_client()
    live = c.post("/calculate", json={"use_live": True}).get_json()
    assert live["live"]["spread_ratio"] < 1 and live["live"]["margin_shift"] < 0
    static = c.post("/calculate", json={"use_live": False}).get_json()
    assert live["presets"]["base"]["roi_usd"] < static["presets"]["base"]["roi_usd"]
