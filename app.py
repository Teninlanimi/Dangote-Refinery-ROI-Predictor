"""
Dangote Refinery IPO ROI Predictor - web app.

Sliders on the page drive the scenario engine in model.py: tweak the
refinery's revenue, net margin and P/E multiple, the naira's expected
depreciation and dividend payout, and the horizon; get the projected ROI in
naira and USD, next to the three anchored preset scenarios and their
probability-weighted expected ROI.

Run:  py app.py          (then open http://127.0.0.1:5000)
"""

from flask import Flask, jsonify, render_template, request

from data import company_data as D
import model

app = Flask(__name__)

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


def run_calculation(payload):
    horizon = 3 if int(payload.get("horizon", 3)) == 3 else 1
    fx_dep = clamp("fx_dep_pct", float(payload.get("fx_dep", LIMITS["fx_dep_pct"][2]))) / 100

    custom = custom_scenario(payload)
    r_custom = model.roi(custom, horizon, model.DEFAULTS["fx_entry"], fx_dep)

    presets = {}
    for name, sc in model.SCENARIOS.items():
        presets[name] = {
            "label": sc["label"],
            "anchor": sc["anchor"],
            "weight": sc["weight"],
            **{k: round(v, 4) for k, v in model.roi(sc, horizon, model.DEFAULTS["fx_entry"], fx_dep).items()},
        }

    # Same levers applied to every horizon, so the chart can show 1/2/3 years
    fx_entry = model.DEFAULTS["fx_entry"]
    horizons_view = {}
    for h in (1, 2, 3):
        per_h = {name: model.roi(sc, h, fx_entry, fx_dep) for name, sc in model.SCENARIOS.items()}
        per_h["custom"] = model.roi(custom, h, fx_entry, fx_dep)
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
    return render_template("index.html", context=static_context())


@app.route("/about")
def about():
    return render_template("about.html", sources=D.SOURCES)


@app.route("/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}
    return jsonify(run_calculation(payload))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "entry_price_ngn": ENTRY})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
