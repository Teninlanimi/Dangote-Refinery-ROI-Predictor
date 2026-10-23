"""
Dangote Refinery IPO - ROI prediction engine.

The idea (mirrors the last project's philosophy: transparent, auditable maths):

  The refinery IPO is priced at N525/share (implied market cap ~N63tn / ~$48bn).
  There is no refinery P&L history long enough to forecast from (it only swung
  to profit in H1 2026 after ~$2bn of start-up losses), so the scenarios are
  BUILT FROM ITS SISTER COMPANIES, which trade on the same exchange,
  management, and macro:

    - DANGOTE CEMENT (FY25: 23.6% net margin, 42% ROE, P/E 13.5x)
        -> the bull case: pricing power + full ramp-up execution.
    - REFINERY ITSELF (H1 2026: 12.5% net margin, $3.6bn annualised profit)
        -> the base case: current run-rate simply holds.
    - DANGOTE SUGAR (FY25: -7.7% net margin, N175bn finance costs)
        -> the bear case: FX devaluation + heavy debt crushes the margin.

  Fair value per share = net income x P/E multiple / shares outstanding.
  ROI = (exit value + dividends - entry cost) / entry cost, in naira and USD.

Run:  py model.py            -> scenario table + sensitivity grid,
                                 writes outputs/ (CSV + markdown report).
Run:  py model.py --apply    -> same, printable only.
"""

import argparse
import csv
import os

from data import company_data as D

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# ---------------------------------------------------------------------------
# Model inputs (defaults; the web app lets you move these)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "fx_entry": D.FX_AT_OFFER,   # 1312.5 NGN/USD (prospectus arithmetic)
    "fx_depreciation": 0.08,     # naira loses 8%/yr vs USD (analyst consensus zone)
    "dividend_payout": 0.25,     # of net income, from year 2 onward
}

# Three scenarios. Each one is anchored on a real, documented data point:
SCENARIOS = {
    "bull": {
        "label": "Bull: cement-like execution",
        "anchor": "DANGOTE CEMENT FY25: 23.6% net margin, P/E 13.5x",
        "weight": 0.25,
        "revenue_usd_bn": 32.0,   # above run-rate: full 650k bpd + petchem
        "net_margin": 0.18,       # approaching DANGCEM's 23.6% over time
        "pe": 14.0,               # slight premium: growth to 1.4m bpd pipeline
        "earnings_growth": 0.18,  # multiple levers (ramp-up, petchem, exports)
        "payout": 0.35,
    },
    "base": {
        "label": "Base: H1 2026 run-rate holds",
        "anchor": "REFINERY H1 2026: 12.5% net margin, $3.6bn annualised profit",
        "weight": 0.50,
        "revenue_usd_bn": 28.8,   # exactly 2x H1 2026
        "net_margin": 0.12,       # H1 2026 actual (12.5%) rounded down
        "pe": 12.0,               # modest discount to DANGCEM's 13.5x
        "earnings_growth": 0.12,  # gradual capacity/ramp-up gains
        "payout": 0.25,
    },
    "bear": {
        "label": "Bear: sugar-like margin stress",
        "anchor": "DANGOTE SUGAR FY25: -7.7% net margin, N175bn finance costs",
        "weight": 0.25,
        "revenue_usd_bn": 26.0,   # volumes/discounts pressure the top line
        "net_margin": 0.05,       # halfway to sugar's -7.7% reality
        "pe": 8.0,                # multiple compression on earnings uncertainty
        "earnings_growth": 0.05,
        "payout": 0.0,            # no dividends in the stress case
    },
}

ENTRY_PRICE = D.OFFER_PRICE_NGN        # 525 NGN, fixed at the offer
ENTRY_MARKET_CAP_USD = D.entry_market_cap_usd_bn()   # ~$48.1bn


# ---------------------------------------------------------------------------
# Core maths
# ---------------------------------------------------------------------------
def fair_price(scenario: dict, horizon: int, fx: float, fx_dep: float) -> dict:
    """Fair value per share at the end of `horizon` years, plus dividends."""
    ni_1 = scenario["revenue_usd_bn"] * scenario["net_margin"]          # $bn, year 1
    shares = D.TOTAL_SHARES_BN
    fx_exit = fx * (1 + fx_dep) ** horizon

    fair_mcap_1 = ni_1 * scenario["pe"]                                 # $bn
    price_1 = fair_mcap_1 / shares                                      # $/share

    # Earnings grow into year 2..horizon; P/E compounding is optimistic,
    # we hold it constant and let growth do the work.
    div_usd = 0.0
    for y in range(2, horizon + 1):
        ni_y = ni_1 * (1 + scenario["earnings_growth"]) ** (y - 1)
        div_usd += ni_y * scenario["payout"] / shares

    if horizon == 1:
        price_exit = price_1
    else:
        ni_h = ni_1 * (1 + scenario["earnings_growth"]) ** (horizon - 1)
        price_exit = ni_h * scenario["pe"] / shares

    return {
        "ni_year1_usd_bn": ni_1,
        "pe": scenario["pe"],
        "fair_mcap_usd_bn": fair_mcap_1,
        "fair_price_usd": price_exit,
        "fair_price_ngn": price_exit * fx_exit,
        "dividends_usd_per_share": div_usd,
        "dividends_ngn_per_share": div_usd * fx_exit,
        "net_income_h_usd_bn": ni_1 * (1 + scenario["earnings_growth"]) ** max(horizon - 1, 0),
    }


def roi(scenario: dict, horizon: int, fx: float, fx_dep: float) -> dict:
    """Naira and USD return on investment at the given horizon."""
    f = fair_price(scenario, horizon, fx, fx_dep)
    exit_ngn = f["fair_price_ngn"]
    exit_usd = f["fair_price_usd"] + f["dividends_usd_per_share"]
    entry_usd = ENTRY_PRICE / fx

    roi_ngn = (exit_ngn + f["dividends_ngn_per_share"] - ENTRY_PRICE) / ENTRY_PRICE
    roi_usd = (exit_usd - entry_usd) / entry_usd
    return {
        "roi_ngn": roi_ngn,
        "roi_usd": roi_usd,
        "roi_ngn_annualised": (1 + roi_ngn) ** (1 / horizon) - 1,
        "roi_usd_annualised": (1 + roi_usd) ** (1 / horizon) - 1,
        "total_return_ngn": exit_ngn + f["dividends_ngn_per_share"],
        "exit_price_usd": f["fair_price_usd"],
        "exit_price_ngn": f["fair_price_ngn"],
        "ni_year1_usd_bn": f["ni_year1_usd_bn"],
        "fair_mcap_usd_bn": f["fair_mcap_usd_bn"],
    }


def expected_roi(horizon: int, fx: float, fx_dep: float) -> dict:
    """Probability-weighted ROI across the three preset scenarios."""
    rois = {name: roi(sc, horizon, fx, fx_dep) for name, sc in SCENARIOS.items()}
    total_w = sum(SCENARIOS[n]["weight"] for n in rois)
    exp_ngn = sum(SCENARIOS[n]["weight"] * r["roi_ngn"] for n, r in rois.items()) / total_w
    exp_usd = sum(SCENARIOS[n]["weight"] * r["roi_usd"] for n, r in rois.items()) / total_w
    return {
        "rois": rois,
        "expected_ngn": exp_ngn,
        "expected_usd": exp_usd,
        "expected_ngn_annualised": (1 + exp_ngn) ** (1 / horizon) - 1,
        "expected_usd_annualised": (1 + exp_usd) ** (1 / horizon) - 1,
    }


def sensitivity_grid(fx: float, fx_dep: float, horizon: int):
    """ROI (naira) per net margin x P/E, holding revenue at the base run-rate."""
    margins = [0.04, 0.08, 0.12, 0.16, 0.20]
    pes = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0]
    rows = []
    for m in margins:
        for pe in pes:
            sc = dict(SCENARIOS["base"], net_margin=m, pe=pe,
                      earnings_growth=0.10, payout=DEFAULTS["dividend_payout"])
            r = roi(sc, horizon, fx, fx_dep)
            rows.append({"net_margin": m, "pe": pe,
                         "roi_ngn": r["roi_ngn"],
                         "roi_usd": r["roi_usd"],
                         "horizon": horizon})
    return rows


# ---------------------------------------------------------------------------
# CLI + report
# ---------------------------------------------------------------------------
def pct(x): return f"{x:+.1%}"


def build_report(horizon: int = 3, fx_dep: float = None) -> str:
    fx = DEFAULTS["fx_entry"]
    if fx_dep is None:
        fx_dep = DEFAULTS["fx_depreciation"]
    exp = expected_roi(horizon, fx, fx_dep)

    lines = []
    a = lines.append
    a("# Dangote Refinery IPO ROI model - scenario report")
    a("")
    a(f"Entry: 4.1bn shares at N525 (offer). Implied market cap "
      f"N{D.entry_market_cap_ngn_trn():.1f}tn (${ENTRY_MARKET_CAP_USD:.1f}bn at "
      f"N{fx:,.1f}/USD). Offer closes 27 October 2026, listing expected"
      f" Nov/Dec 2026 on the NGX.")
    a("")
    a(f"Holding {horizon} year(s). Assumptions: naira depreciates "
      f"{fx_dep:.0%}/yr; dividends from year 2 at scenario payout rates.")
    a(f"Entry price in USD: ${D.OFFER_PRICE_NGN / fx:.3f}.")
    a("")
    a("| Scenario (anchor) | Rev $bn | Net margin | P/E | Fair price N | FY1 profit $bn | ROI (naira) | ROI (USD) |")
    a("|---|---|---|---|---|---|---|---|")
    for name, sc in SCENARIOS.items():
        r = exp["rois"][name]
        a(f"| {sc['label']} - {sc['anchor']} ({sc['weight']:.0%} weight) | "
          f"{sc['revenue_usd_bn']:.1f} | {sc['net_margin']:.0%} | "
          f"{sc['pe']:.0f}x | {r['exit_price_ngn']:,.0f} | "
          f"{r['ni_year1_usd_bn']:.1f} | {pct(r['roi_ngn'])} | {pct(r['roi_usd'])} |")
    a("")
    a(f"Probability-weighted expected ROI over {horizon} year(s): "
      f"**{pct(exp['expected_ngn'])} in naira** ({pct(exp['expected_ngn_annualised'])} "
      f"annualised), {pct(exp['expected_usd'])} in USD.")
    a("")
    a("## What the brother-companies say")
    a("")
    a("- Dangote Cement FY25: N4.31trn revenue, N1.01trn profit (23.6% net margin), ROE 42.3%, trades at 13.5x P/E, N45 dividend.")
    a("- Dangote Sugar FY25: N829bn revenue (+24.6%), N64.1bn LOSS (-7.7% net margin), N175bn finance costs - FX + debt can eat an entire Dangote business's margin.")
    a("- Refinery H1 2026: $14.4bn revenue, $1.8bn net income (12.5% net margin) after $1.51bn (2024) and $476m (2025) start-up losses; $3.65bn of debt.")
    a("")
    a("The IPO price at N525 implies about 13.4x the refinery's annualised H1 2026")
    a("profit - almost exactly Dangote Cement's 13.5x. So the public-offer price")
    a("already assumes cement-like faith in a business with one half-year of")
    a("profits and $3.65bn of debt. The upside case earns DANGCEM-like returns;")
    a("the downside case is sugar-shaped.")
    a("")
    a("Key risks not in the maths: the 30% greenshoe dilution, the private-placement")
    a("365-day lock-up expiry, FX liberalisation policy reversals, crude supply")
    a("scarcity from the NNPC's reduced stake, and cash conversion/Naira dollar-")
    a("remittance rules for the promised dollar dividends.")
    a("")
    a("*This is an educational scenario model, not investment advice.*")
    return "\n".join(lines)


def write_outputs(horizon: int, fx_dep: float) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = build_report(horizon, fx_dep)
    report_path = os.path.join(OUTPUT_DIR, "scenario_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    grid = sensitivity_grid(DEFAULTS["fx_entry"], fx_dep, horizon)
    grid_path = os.path.join(OUTPUT_DIR, "sensitivity_pe_margin.csv")
    with open(grid_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(grid[0].keys()))
        w.writeheader()
        w.writerows(grid)
    return report_path


def main():
    ap = argparse.ArgumentParser(description="Dangote refinery IPO ROI model")
    ap.add_argument("--horizon", type=int, default=3, choices=[1, 2, 3])
    ap.add_argument("--fx-dep", type=float, default=0.08, help="naira depreciation per year, e.g. 0.08")
    ap.add_argument("--print-only", action="store_true", help="don't write outputs/")
    args = ap.parse_args()

    print(build_report(args.horizon, args.fx_dep))
    if not args.print_only:
        path = write_outputs(args.horizon, args.fx_dep)
        print(f"\nWritten: {os.path.relpath(path, BASE_DIR)}")


if __name__ == "__main__":
    main()
