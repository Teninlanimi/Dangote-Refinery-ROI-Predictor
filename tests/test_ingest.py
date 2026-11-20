from datetime import date

from sqlalchemy import func, select

from pipeline import db, ingest, market
from pipeline.sources import Observation, SourceError

TODAY = date(2026, 11, 20)


def count(url, series):
    with db.get_engine(url).connect() as c:
        return c.execute(select(func.count()).select_from(db.market_observations)
                         .where(db.market_observations.c.series == series)).scalar()


def test_first_run_backfills_then_second_run_adds_nothing(db_url, fake_fetchers):
    r1 = ingest.run(db_url, fake_fetchers, TODAY)
    assert r1["status"] == "success"
    n_brent = count(db_url, "brent_usd")
    assert n_brent > 200 and count(db_url, "usdngn") == 1

    r2 = ingest.run(db_url, fake_fetchers, TODAY)
    assert r2["status"] == "success" and r2["rows_inserted"] == 0
    assert count(db_url, "brent_usd") == n_brent


def test_bad_value_is_rejected_and_logged(db_url, fake_fetchers):
    fake_fetchers["usdngn"] = lambda since=None: [Observation("usdngn", TODAY, 0.9, "test")]
    r = ingest.run(db_url, fake_fetchers, TODAY)
    assert r["status"] == "partial"
    assert count(db_url, "usdngn") == 0
    with db.get_engine(db_url).connect() as c:
        fails = market.recent_checks(c)
    assert any(x["series"] == "usdngn" and x["outcome"] == "fail" for x in fails)


def test_source_outage_does_not_block_other_series(db_url, fake_fetchers):
    def down(since=None):
        raise SourceError("timeout")
    fake_fetchers["usdngn"] = down
    r = ingest.run(db_url, fake_fetchers, TODAY)
    assert r["status"] == "partial"
    assert count(db_url, "brent_usd") > 0


def test_everything_down_is_failed(db_url):
    def down(since=None):
        raise SourceError("timeout")
    r = ingest.run(db_url, {"brent_usd": down, "usdngn": down}, TODAY)
    assert r["status"] == "failed"


def test_big_jump_is_stored_but_flagged(db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    fake_fetchers["usdngn"] = lambda since=None: [Observation("usdngn", TODAY, 1800.0, "test")]
    ingest.run(db_url, fake_fetchers, TODAY)
    with db.get_engine(db_url).connect() as c:
        latest = market.latest(c, "usdngn", TODAY)
    assert latest["value"] == 1800.0 and latest["quality"] == "warn"


def test_snapshot_crude_factor(db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    snap = market.snapshot(db.get_engine(db_url), TODAY)
    assert snap["available"] == {"fx": True, "crude": True, "crack": True}
    assert abs(snap["crack"]["value"] - 29.4) < 1e-9
    assert abs(snap["spread_ratio"] - 1.0) < 1e-9
    assert abs(snap["crude_factor"] - 1.0) < 1e-9      # flat price -> factor 1
    assert snap["usdngn"]["value"] == 1450.0
