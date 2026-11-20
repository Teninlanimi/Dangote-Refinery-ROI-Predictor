"""
Read side of the pipeline: what the web app asks the database for.

The two links between live data and the ROI model:

  1. FX starting point - the projected exit exchange rate starts from today's
     USD/NGN instead of the prospectus rate (N1,312.5), because the naira has
     moved since the offer priced.
  2. Crude factor - refinery revenue is scaled by (latest Brent / average
     Brent over H1 2026), the half-year the $28.8bn run-rate revenue came
     from. Product prices track crude, so revenue does too; the model keeps
     net margin as a % of revenue, so profit scales with it.
  3. Crack spread - the 3-2-1 spread (2 bbl petrol + 1 bbl diesel - 3 bbl
     crude) is the market's refining margin. Its ratio to the H1 2026 average
     moves net margin (model.crack_margin_shift), so dearer crude alone no
     longer inflates profit.
"""

from datetime import date, timedelta

from sqlalchemy import func, select

from pipeline import db

T_OBS, T_RUNS, T_CHECKS = db.market_observations, db.ingestion_runs, db.check_results

# The revenue run-rate in data/company_data.py is 2 x H1 2026 revenue.
REFERENCE_START = date(2026, 1, 1)
REFERENCE_END = date(2026, 6, 30)
MIN_REFERENCE_DAYS = 60          # need most of the half-year's trading days
MIN_TREND_SPAN_DAYS = 30         # don't annualise less than a month of FX moves
GALLONS_PER_BARREL = 42
CRACK_LOOKBACK_DAYS = 30         # newest date on which all three prices exist


def latest(conn, series: str, today: date = None):
    row = conn.execute(
        select(T_OBS.c.value, T_OBS.c.observed_on, T_OBS.c.quality, T_OBS.c.source)
        .where(T_OBS.c.series == series)
        .order_by(T_OBS.c.observed_on.desc()).limit(1)
    ).first()
    if row is None:
        return None
    today = today or db.utcnow().date()
    return {"value": row.value, "date": row.observed_on.isoformat(), "quality": row.quality,
            "source": row.source, "age_days": (today - row.observed_on).days}


def history(conn, series: str, days: int = 365, today: date = None) -> list:
    today = today or db.utcnow().date()
    rows = conn.execute(
        select(T_OBS.c.observed_on, T_OBS.c.value)
        .where(T_OBS.c.series == series, T_OBS.c.observed_on >= today - timedelta(days=days))
        .order_by(T_OBS.c.observed_on)
    ).all()
    return [{"date": r.observed_on.isoformat(), "value": r.value} for r in rows]


def brent_reference(conn):
    avg, n = conn.execute(
        select(func.avg(T_OBS.c.value), func.count())
        .where(T_OBS.c.series == "brent_usd",
               T_OBS.c.observed_on.between(REFERENCE_START, REFERENCE_END))
    ).one()
    if not n or n < MIN_REFERENCE_DAYS:
        return None
    return {"value": float(avg), "days": n,
            "period": f"{REFERENCE_START.isoformat()} to {REFERENCE_END.isoformat()}"}


def fx_trend(conn):
    """Annualised naira depreciation observed in the stored USD/NGN history."""
    first = conn.execute(select(T_OBS.c.observed_on, T_OBS.c.value)
                         .where(T_OBS.c.series == "usdngn")
                         .order_by(T_OBS.c.observed_on).limit(1)).first()
    last = conn.execute(select(T_OBS.c.observed_on, T_OBS.c.value)
                        .where(T_OBS.c.series == "usdngn")
                        .order_by(T_OBS.c.observed_on.desc()).limit(1)).first()
    if not first or not last:
        return None
    span = (last.observed_on - first.observed_on).days
    if span < MIN_TREND_SPAN_DAYS:
        return {"annualised": None, "span_days": span}
    rate = (last.value / first.value) ** (365 / span) - 1
    return {"annualised": rate, "span_days": span}


def _by_date(conn, series: str, start: date, end: date) -> dict:
    rows = conn.execute(
        select(T_OBS.c.observed_on, T_OBS.c.value)
        .where(T_OBS.c.series == series, T_OBS.c.observed_on.between(start, end))
    ).all()
    return {r.observed_on: r.value for r in rows}


def crack_321(brent_bbl: float, gasoline_gal: float, diesel_gal: float) -> float:
    """3-2-1 crack spread in USD per barrel of crude."""
    g = gasoline_gal * GALLONS_PER_BARREL
    d = diesel_gal * GALLONS_PER_BARREL
    return (2 * g + d - 3 * brent_bbl) / 3


def crack_spreads(conn, start: date, end: date) -> list:
    """Daily 3-2-1 spread on every date where Brent, petrol and diesel all exist."""
    b = _by_date(conn, "brent_usd", start, end)
    g = _by_date(conn, "gasoline_nyh", start, end)
    d = _by_date(conn, "diesel_nyh", start, end)
    days = sorted(set(b) & set(g) & set(d))
    return [{"date": day.isoformat(), "value": crack_321(b[day], g[day], d[day])} for day in days]


def latest_crack(conn, today: date = None):
    today = today or db.utcnow().date()
    rows = crack_spreads(conn, today - timedelta(days=CRACK_LOOKBACK_DAYS), today)
    return rows[-1] if rows else None


def crack_reference(conn):
    rows = crack_spreads(conn, REFERENCE_START, REFERENCE_END)
    if len(rows) < MIN_REFERENCE_DAYS:
        return None
    avg = sum(r["value"] for r in rows) / len(rows)
    if avg <= 0:
        return None
    return {"value": avg, "days": len(rows),
            "period": f"{REFERENCE_START.isoformat()} to {REFERENCE_END.isoformat()}"}


EXPORT_COLUMNS = [
    ("date", None),
    ("brent_usd_per_bbl", "brent_usd"),
    ("petrol_nyh_usd_per_gal", "gasoline_nyh"),
    ("diesel_nyh_usd_per_gal", "diesel_nyh"),
    ("crack_321_usd_per_bbl", None),
    ("ngn_per_usd", "usdngn"),
]


def export_prices(conn) -> list:
    """Every stored day as one row: all series side by side, plus the 3-2-1 spread.
    Blank where a source didn't publish that day."""
    rows = conn.execute(select(T_OBS.c.series, T_OBS.c.observed_on, T_OBS.c.value)).all()
    by_day = {}
    for r in rows:
        by_day.setdefault(r.observed_on, {})[r.series] = r.value
    out = []
    for day in sorted(by_day):
        v = by_day[day]
        crack = (crack_321(v["brent_usd"], v["gasoline_nyh"], v["diesel_nyh"])
                 if all(k in v for k in ("brent_usd", "gasoline_nyh", "diesel_nyh")) else None)
        row = {"date": day.isoformat()}
        for col, series in EXPORT_COLUMNS[1:]:
            row[col] = crack if col == "crack_321_usd_per_bbl" else v.get(series)
        out.append(row)
    return out


def recent_runs(conn, limit: int = 20) -> list:
    rows = conn.execute(select(T_RUNS).order_by(T_RUNS.c.id.desc()).limit(limit)).mappings().all()
    return [dict(r) for r in rows]


def recent_checks(conn, limit: int = 60) -> list:
    rows = conn.execute(select(T_CHECKS).order_by(T_CHECKS.c.id.desc()).limit(limit)).mappings().all()
    return [dict(r) for r in rows]


def last_success(conn):
    return conn.execute(
        select(T_RUNS.c.finished_at)
        .where(T_RUNS.c.status.in_(("success", "partial")))
        .order_by(T_RUNS.c.id.desc()).limit(1)
    ).scalar()


def snapshot(engine=None, today: date = None) -> dict:
    """Everything the dashboard needs about live data, in one dict."""
    engine = engine or db.get_engine()
    with engine.connect() as conn:
        brent = latest(conn, "brent_usd", today)
        fx = latest(conn, "usdngn", today)
        ref = brent_reference(conn)
        trend = fx_trend(conn)
        runs = recent_runs(conn, 1)
        gasoline = latest(conn, "gasoline_nyh", today)
        diesel = latest(conn, "diesel_nyh", today)
        crack = latest_crack(conn, today)
        crack_ref = crack_reference(conn)

    crude_factor = brent["value"] / ref["value"] if (brent and ref) else None
    spread_ratio = crack["value"] / crack_ref["value"] if (crack and crack_ref) else None
    return {
        "brent": brent,
        "gasoline": gasoline,
        "diesel": diesel,
        "usdngn": fx,
        "brent_reference": ref,
        "crude_factor": crude_factor,
        "crack": crack,
        "crack_reference": crack_ref,
        "spread_ratio": spread_ratio,
        "fx_trend": trend,
        "last_run": runs[0] if runs else None,
        "available": {"fx": fx is not None, "crude": crude_factor is not None,
                      "crack": spread_ratio is not None},
    }
