import csv
import io
from datetime import date

import pytest

from pipeline import ingest

TODAY = date(2026, 11, 20)


@pytest.fixture
def client(db_url):
    import app as app_module
    app_module.app.testing = True
    app_module.limiter.reset()
    return app_module.app.test_client()


def read_csv(resp):
    return list(csv.DictReader(io.StringIO(resp.data.decode())))


def test_prices_csv(client, db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    r = client.get("/download/prices.csv")
    assert r.status_code == 200 and r.mimetype == "text/csv"
    assert "attachment" in r.headers["Content-Disposition"]
    assert "FRED" in r.headers["X-Data-Sources"]
    rows = read_csv(r)
    assert list(rows[0]) == ["date", "brent_usd_per_bbl", "petrol_nyh_usd_per_gal",
                             "diesel_nyh_usd_per_gal", "crack_321_usd_per_bbl", "ngn_per_usd"]
    last = rows[-1]
    assert last["date"] == "2026-11-19" and float(last["ngn_per_usd"]) == 1450.0
    assert abs(float(last["crack_321_usd_per_bbl"]) - 29.4) < 1e-9
    assert rows[0]["ngn_per_usd"] == ""          # FX history starts later: left blank


def test_runs_and_checks_csv(client, db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    runs = read_csv(client.get("/download/pipeline-runs.csv"))
    checks = read_csv(client.get("/download/data-checks.csv"))
    assert runs[0]["status"] == "success"
    assert {c["check_name"] for c in checks} >= {"range", "freshness"}


def test_empty_database_gives_header_only(client):
    rows = client.get("/download/prices.csv").data.decode().strip().splitlines()
    assert rows == ["date,brent_usd_per_bbl,petrol_nyh_usd_per_gal,diesel_nyh_usd_per_gal,crack_321_usd_per_bbl,ngn_per_usd"]


def test_download_limit(client):
    for _ in range(30):
        assert client.get("/download/prices.csv").status_code == 200
    r = client.get("/download/prices.csv")
    assert r.status_code == 429
    assert "Too many requests" in r.data.decode()


def test_api_limit_returns_json(client):
    for _ in range(60):
        client.get("/api/market")
    r = client.get("/api/market")
    assert r.status_code == 429 and "error" in r.get_json()


def test_limits_are_per_visitor(client):
    for _ in range(30):
        client.get("/download/prices.csv", environ_base={"REMOTE_ADDR": "10.0.0.1"})
    assert client.get("/download/prices.csv", environ_base={"REMOTE_ADDR": "10.0.0.1"}).status_code == 429
    assert client.get("/download/prices.csv", environ_base={"REMOTE_ADDR": "10.0.0.2"}).status_code == 200
