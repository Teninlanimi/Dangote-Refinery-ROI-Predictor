from datetime import date

from pipeline import checks


def test_range_rejects_broken_values():
    assert checks.check_range("brent_usd", 0.0).outcome == "fail"
    assert checks.check_range("brent_usd", 7000.0).outcome == "fail"   # price in cents
    assert checks.check_range("usdngn", 1.08).outcome == "fail"        # EUR/USD by mistake
    assert checks.check_range("usdngn", float("nan")).outcome == "fail"
    assert checks.check_range("usdngn", 1450.0).outcome == "pass"


def test_jump_flags_big_moves_only():
    assert checks.check_jump("usdngn", 1450, None).outcome == "pass"
    assert checks.check_jump("usdngn", 1500, 1450).outcome == "pass"
    assert checks.check_jump("usdngn", 1700, 1450).outcome == "warn"
    assert checks.check_jump("brent_usd", 55, 70).outcome == "warn"


def test_freshness():
    today = date(2026, 11, 20)
    assert checks.check_freshness("usdngn", date(2026, 11, 19), today).outcome == "pass"
    assert checks.check_freshness("usdngn", date(2026, 11, 1), today).outcome == "warn"
