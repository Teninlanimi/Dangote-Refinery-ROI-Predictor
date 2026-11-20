import pytest

from pipeline import ingest

TODAY = __import__("datetime").date(2026, 11, 20)


@pytest.fixture
def client(db_url):
    import app as app_module
    app_module.app.testing = True
    return app_module.app.test_client()


def test_static_mode_reproduces_readme_numbers(client):
    d = client.post("/calculate", json={"horizon": 3, "use_live": False}).get_json()
    assert d["live"]["mode"] == "static"
    assert round(d["presets"]["base"]["roi_ngn"], 3) == 0.418
    assert round(d["expected"]["roi_ngn"], 3) == 0.554


def test_live_mode_uses_db(client, db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    d = client.post("/calculate", json={"horizon": 3, "use_live": True}).get_json()
    assert d["live"]["mode"] == "live"
    assert d["live"]["fx_now"] == 1450.0
    static = client.post("/calculate", json={"horizon": 3, "use_live": False}).get_json()
    # weaker naira at the start -> higher naira ROI, same USD ROI (crude factor is 1 here)
    assert d["presets"]["base"]["roi_ngn"] > static["presets"]["base"]["roi_ngn"]
    assert d["presets"]["base"]["roi_usd"] == static["presets"]["base"]["roi_usd"]


def test_pages_and_health(client, db_url, fake_fetchers):
    assert client.get("/health").get_json()["status"] == "degraded"   # no ingest yet
    ingest.run(db_url, fake_fetchers, TODAY)
    h = client.get("/health").get_json()
    assert h["status"] == "ok" and h["database"] == "ok"
    for path in ("/", "/calculator", "/about", "/status", "/api/market"):
        assert client.get(path).status_code == 200, path
    assert b"1,450.0" in client.get("/").data


def test_admin_ingest_requires_token(client):
    assert client.post("/admin/ingest").status_code == 403


def test_bad_input(client):
    assert client.post("/calculate", json={"pe": "abc"}).status_code == 400


def test_market_page_without_data(client):
    page = client.get("/").data.decode()
    assert "No market data has been loaded yet" in page
    assert "13.3 times" in page          # hero still works on offer-date figures


def test_market_page_with_data(client, db_url, fake_fetchers):
    ingest.run(db_url, fake_fetchers, TODAY)
    page = client.get("/").data.decode()
    assert "What today's market does to the model" in page
    assert "chart-brent" in page and "chart-crack" in page
