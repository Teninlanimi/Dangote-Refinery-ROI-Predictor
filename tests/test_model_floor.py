import model


def test_loss_making_scenario_floors_at_total_loss():
    """A deep margin cut must give at worst -100%, never a crash or a complex number."""
    bear = model.with_market(model.SCENARIOS["bear"], 1.0, -model.MAX_MARGIN_SHIFT)
    assert bear["net_margin"] < 0
    for h in (1, 2, 3):
        r = model.roi(bear, h, model.DEFAULTS["fx_entry"], 0.08, 1400.0)
        for k in ("roi_ngn", "roi_usd", "roi_ngn_annualised", "roi_usd_annualised"):
            assert isinstance(r[k], float) and r[k] >= -1.0
        assert r["exit_price_ngn"] == 0.0


def test_live_mode_with_deep_margin_cut_renders(monkeypatch):
    import app
    snap = {"usdngn": {"value": 1400.0, "date": "2026-11-25"}, "crude_factor": 1.0,
            "brent": {"value": 70.0, "date": "2026-11-25"}, "brent_reference": {"value": 70.0},
            "crack": {"value": 5.0, "date": "2026-11-25"}, "crack_reference": {"value": 30.0},
            "spread_ratio": 5 / 30, "available": {"fx": True, "crude": True, "crack": True}}
    d = app.run_calculation({"horizon": 3, "use_live": True}, snap)
    assert d["presets"]["bear"]["roi_ngn"] >= -1.0
    assert d["live"]["margin_shift"] == -model.MAX_MARGIN_SHIFT
