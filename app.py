"""
Dangote Refinery IPO ROI Predictor - web app.

Sliders on the page drive the scenario engine in model.py: tweak the
refinery's revenue, net margin and P/E multiple, the naira's expected
depreciation and dividend payout, and the horizon; get the projected ROI in
naira and USD, next to the three anchored preset scenarios and their
probability-weighted expected ROI.

Live mode (default when the database has data): the exit exchange rate starts
from today's USD/NGN, revenue moves with Brent crude, and net margin moves with
the 3-2-1 crack spread - all pulled on a schedule by pipeline/ (see
pipeline/market.py and model.crack_margin_shift for the exact links).

Run:  py app.py          (then open http://127.0.0.1:5000)
Data: py -m pipeline.ingest   (pull crude + FX once)
"""

import hmac
import logging
from datetime import timedelta, timezone

from flask import Flask, abort, jsonify, render_template, request

import config
from data import company_data as D
import model
from pipeline import db, ingest, market

app = Flask(__name__)
app.json.sort_keys = False   # keep bull / base / bear in model order
log = logging.getLogger("roi-app")

try:
    db.init_db()
except Exception:  # the app still serves the static model if the DB is down
    log.exception("database init failed - running without live data")

ENTRY = D.OFFER_PRICE_NGN          # N525

# Slider bounds (net margin entered as percent on the page)
LIMITS = {
    "revenue_usd_bn": (20.0, 40.0, 28.8),
    "net_margin_pct": (-2.0, 24.0, 12.0),
    "pe": (5.0, 18.0, 12.0),
    "earnings_growth_pct": (0.0, 25.0, 12.0),
    "fx_dep_pct": (0.0, 20.0, 8.0),
    "payout_pct": (0.0, 60.0, 25.0),
}


def clamp(name, value):
    lo, hi, _ = LIMITS[name]
    return min(hi, max(lo, value))


def custom_scenario(payload):
    pct = lambda name, key="pct": clamp(key, float(payload.get(name, LIMITS[key][2]))) / 100
    return {
        "revenue_usd_bn": clamp("revenue_usd_bn", float(payload.get("revenue_usd_bn", 28.8))),
        "net_margin": pct("net_margin", "net_margin_pct"),
        "pe": clamp("pe", float(payload.get("pe", 12.0))),
        "earnings_growth": pct("earnings_growth", "earnings_growth_pct"),
        "payout": pct("payout", "payout_pct"),
    }


def safe_snapshot():
    """Live market snapshot, or None if the database can't be read."""
    try:
        return market.snapshot()
    except Exception:
        log.exception("could not read market snapshot")
        return None


def live_inputs(use_live: bool, snap):
    """(fx_now, crude_factor, margin_shift, description) for this request."""
    if not use_live or not snap:
        return None, None, 0.0, {"mode": "static", "fx_now": None, "crude_factor": None,
                                 "margin_shift": None}
    fx_now = snap["usdngn"]["value"] if snap["available"]["fx"] else None
    crude = snap["crude_factor"] if snap["available"]["crude"] else None
    ratio = snap["spread_ratio"] if snap["available"].get("crack") else None
    shift = model.crack_margin_shift(ratio, crude) if ratio else 0.0
    mode = "live" if (fx_now or crude or ratio) else "static"
    return fx_now, crude, shift, {
        "mode": mode,
        "fx_now": round(fx_now, 2) if fx_now else None,
        "fx_date": snap["usdngn"]["date"] if fx_now else None,
        "crude_factor": round(crude, 4) if crude else None,
        "brent": round(snap["brent"]["value"], 2) if crude else None,
        "brent_date": snap["brent"]["date"] if crude else None,
        "brent_reference": round(snap["brent_reference"]["value"], 2) if crude else None,
        "crack": round(snap["crack"]["value"], 2) if ratio else None,
        "crack_date": snap["crack"]["date"] if ratio else None,
        "crack_reference": round(snap["crack_reference"]["value"], 2) if ratio else None,
        "spread_ratio": round(ratio, 4) if ratio else None,
        "margin_shift": round(shift, 4) if ratio else None,
    }


def run_calculation(payload, snap=None):
    horizon = 3 if int(payload.get("horizon", 3)) == 3 else 1
    fx_dep = clamp("fx_dep_pct", float(payload.get("fx_dep", LIMITS["fx_dep_pct"][2]))) / 100
    fx_now, crude, shift, live = live_inputs(bool(payload.get("use_live", True)), snap)
    fx_entry = model.DEFAULTS["fx_entry"]
    scenarios = {name: model.with_market(sc, crude, shift) for name, sc in model.SCENARIOS.items()}

    custom = model.with_market(custom_scenario(payload), crude, shift)
    r_custom = model.roi(custom, horizon, fx_entry, fx_dep, fx_now)

    presets = {}
    for name, sc in scenarios.items():
        presets[name] = {
            "label": sc["label"],
            "anchor": sc["anchor"],
            "weight": sc["weight"],
            **{k: round(v, 4) for k, v in model.roi(sc, horizon, fx_entry, fx_dep, fx_now).items()},
        }

    # Same levers applied to every horizon, so the chart can show 1/2/3 years
    horizons_view = {}
    for h in (1, 2, 3):
        per_h = {name: model.roi(sc, h, fx_entry, fx_dep, fx_now) for name, sc in scenarios.items()}
        per_h["custom"] = model.roi(custom, h, fx_entry, fx_dep, fx_now)
        horizons_view[str(h)] = {
            name: {"roi_ngn": round(v["roi_ngn"], 4), "roi_usd": round(v["roi_usd"], 4)}
            for name, v in per_h.items()
        }

    total_weight = sum(sc["weight"] for sc in model.SCENARIOS.values())
    expected_ngn = sum(model.SCENARIOS[n]["weight"] * p["roi_ngn"] for n, p in presets.items()) / total_weight
    expected_usd = sum(model.SCENARIOS[n]["weight"] * p["roi_usd"] for n, p in presets.items()) / total_weight

    return {
        "horizon": horizon,
        "entry_price_ngn": ENTRY,
        "entry_price_usd": round(ENTRY / model.DEFAULTS["fx_entry"], 3),
        "fx_dep": fx_dep,
        "custom": {
            "inputs": {k: round(v, 4) for k, v in custom.items()},
            **{k: round(v, 4) for k, v in r_custom.items()},
        },
        "presets": presets,
        "horizons": horizons_view,
        "expected": {
            "roi_ngn": round(expected_ngn, 4),
            "roi_usd": round(expected_usd, 4),
            "roi_ngn_annualised": round((1 + expected_ngn) ** (1 / horizon) - 1, 4),
            "roi_usd_annualised": round((1 + expected_usd) ** (1 / horizon) - 1, 4),
        },
        "context": static_context(),
        "live": live,
    }


def static_context():
    return {
        "entry_market_cap_ngn_trn": round(D.entry_market_cap_ngn_trn(), 1),
        "entry_market_cap_usd_bn": round(D.entry_market_cap_usd_bn(), 1),
        "annualised_h1_2026_profit_bn": D.REFINERY["annualised_net_income_usd_bn"],
        "implied_entry_pe": round(D.entry_market_cap_usd_bn() / D.REFINERY["annualised_net_income_usd_bn"], 1),
        "cement_pe": D.DANGOTE_CEMENT["pe_2026"],
    }


@app.route("/")
def index():
    return render_template("index.html", context=static_context(), live=safe_snapshot())


@app.route("/about")
def about():
    return render_template("about.html", sources=D.SOURCES)


@app.route("/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(run_calculation(payload, safe_snapshot()))
    except (TypeError, ValueError):
        return jsonify({"error": "Inputs must be numbers."}), 400


@app.route("/api/market")
def api_market():
    """Latest values plus history, for charts or anyone who wants the data."""
    days = min(max(request.args.get("days", 180, type=int), 1), 3650)
    try:
        engine = db.get_engine()
        with engine.connect() as conn:
            hist = {s: market.history(conn, s, days)
                    for s in ("brent_usd", "gasoline_nyh", "diesel_nyh", "usdngn")}
            today = db.utcnow().date()
            hist["crack_321"] = market.crack_spreads(conn, today - timedelta(days=days), today)
        return jsonify({"snapshot": market.snapshot(engine), "history": hist})
    except Exception:
        log.exception("api/market failed")
        return jsonify({"error": "market data unavailable"}), 503


@app.route("/status")
def status():
    """Pipeline health page: recent runs and every data-check outcome."""
    try:
        with db.get_engine().connect() as conn:
            runs = market.recent_runs(conn, 20)
            checks = market.recent_checks(conn, 60)
        error = None
    except Exception as exc:
        runs, checks, error = [], [], str(exc)
    return render_template("status.html", runs=runs, checks=checks,
                           snap=safe_snapshot(), error=error)


@app.route("/admin/ingest", methods=["POST"])
def admin_ingest():
    """Trigger a pipeline run by hand: header  X-Ingest-Token: <INGEST_TOKEN>."""
    token = request.headers.get("X-Ingest-Token", "")
    if not config.INGEST_TOKEN or not hmac.compare_digest(token, config.INGEST_TOKEN):
        abort(403)
    return jsonify(ingest.run())


@app.route("/health")
def health():
    """Liveness + data freshness. 503 only if the database is unreachable."""
    body = {"status": "ok", "entry_price_ngn": ENTRY}
    try:
        with db.get_engine().connect() as conn:
            last = market.last_success(conn)
        body["database"] = "ok"
        if last is None:
            body.update(status="degraded", data="no successful ingest yet")
        else:
            if last.tzinfo is None:          # SQLite returns naive datetimes
                last = last.replace(tzinfo=timezone.utc)
            last = last.astimezone(timezone.utc)
            age_h = (db.utcnow() - last).total_seconds() / 3600
            body["last_ingest_utc"] = last.isoformat()
            body["data_age_hours"] = round(age_h, 1)
            if age_h > 36:
                body["status"] = "degraded"
        return jsonify(body)
    except Exception:
        log.exception("health check: database unreachable")
        body.update(status="error", database="unreachable")
        return jsonify(body), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
