"""
Hard numbers for the Dangote refinery IPO ROI model — all verified facts and
the URLs they came from. The model (model.py) reads only from this module, so
every assumption is auditable in one place.

Figures are as reported publicly as of 13 October 2026 (offer still open,
closes 27 Oct 2026; NGX listing expected Nov/Dec 2026).
"""

# ---------------------------------------------------------------------------
# The IPO itself (confirmed figures from the SEC-approved prospectus)
# ---------------------------------------------------------------------------
OFFER_PRICE_NGN = 525.0          # per share, retail offer price
OFFER_PRICE_USD = 0.40           # prospectus USD equivalent
OFFER_SHARES_BN = 4.1            # billion ordinary shares offered
TOTAL_SHARES_BN = 120.13         # billion shares registered by the SEC
GROSS_PROCEEDS_NGN_TRN = 2.15    # ~N2.15 trillion if fully subscribed
GREENSHOE_PCT = 0.30             # up to 30% extra shares if oversubscribed
PRIVATE_PLACEMENT_USD = 2.5      # $2.5bn private placement, July 2026
PLACEMENT_PRICE_USD = 0.35       # placement priced BELOW the retail offer
PLACEMENT_IMPLIED_VAL_BN = 40.0  # ~$40bn implied at the July 2026 placement

# Implied exchange rate from the prospectus: 525 / 0.40
FX_AT_OFFER = OFFER_PRICE_NGN / OFFER_PRICE_USD   # 1312.5 NGN per USD

# Reported implied valuation at IPO pricing: ~N65.2tn ($47.8-49bn).
# 120.13bn shares x N525 = N63.07tn — we use share-count arithmetic
# (N63.07tn / $48.1bn at FX_AT_OFFER) for all internal maths.
IMPLIES_VALUATION_NGN_TRN_REPORTED = 65.2

# ---------------------------------------------------------------------------
# The refinery's own track record (the subject of the IPO)
# ---------------------------------------------------------------------------
REFINERY = {
    "name": "Dangote Petroleum Refinery & Petrochemicals FZE",
    "capacity_bpd": 650_000,
    "expansion_target_bpd_2029": 1_400_000,
    "location": "Lekki Free Zone, Lagos",
    "loss_2024_usd_bn": 1.51,
    "loss_2025_usd_bn": 0.476,
    "h1_2026_revenue_usd_bn": 14.4,        # N19.13tn reported
    "h1_2026_gross_profit_usd_bn": 2.6,    # N3.4tn reported
    "h1_2026_net_income_usd_bn": 1.8,
    "debt_usd_bn": 3.65,                   # company estimate
    # Derived: annualised run-off numbers used as the base-case anchor
    "annualised_revenue_usd_bn": 14.4 * 2,     # 28.8
    "annualised_net_income_usd_bn": 1.8 * 2,   # 3.6
    "h1_2026_net_margin": 1.8 / 14.4,          # 12.5%
    "h1_2026_gross_margin": 2.6 / 14.4,        # 18.1%
}

# ---------------------------------------------------------------------------
# Benchmark #1 — Dangote Cement Plc (NGX: DANGCEM), FY 2025 audited
# Scenarios anchored on this: the profitable, pricing-power case.
# ---------------------------------------------------------------------------
DANGOTE_CEMENT = {
    "revenue_ngn_trn_2025": 4.306,      # +20.28% YoY (2024: 3.58)
    "revenue_ngn_trn_2024": 3.58,
    "pat_ngn_trn_2025": 1.014,          # profit after tax, +101.67% YoY
    "pat_ngn_trn_2024": 0.50325,
    "net_margin_2025": 0.2357,
    "net_margin_2024": 0.1406,
    "gross_margin_2025": 0.6205,
    "ebitda_margin_2025": 0.460,
    "roe_2025": 0.4233,
    "roa_2025": 0.1631,
    "pe_2026": 13.53,                   # at N809.90 (Mar 2026)
    "pb_2026": 5.18,
    "ev_ebitda": 7.24,
    "market_cap_ngn_trn": 13.57,
    "finance_costs_ngn_bn_2025": 351.5,  # down from 700.3 (leveraging down)
}

# ---------------------------------------------------------------------------
# Benchmark #2 — Dangote Sugar Refinery Plc (NGX: DANGSUGAR), FY 2025 audited
# Scenarios anchored on this: the FX-and-debt-stressed downside case.
# ---------------------------------------------------------------------------
DANGOTE_SUGAR = {
    "revenue_ngn_bn_2025": 829.21,      # +24.57% YoY (Nairaametrics, FY25)
    "revenue_ngn_bn_2024": 665.66,
    "net_loss_ngn_bn_2025": 64.12,      # vs N192.62bn loss in 2024
    "net_loss_ngn_bn_2024": 192.62,
    "net_margin_2025": -64.12 / 829.21,  # -7.73%
    "finance_costs_ngn_bn_2025": 175.35,
    "equity_ngn_bn_2025": 128.98,
    "revenue_usd_m_2025": 432.6,
    "loss_usd_m_2025": 41.7,
}

SOURCES = {
    "ipo": {
        "Daba Research live IPO tracker (verified 13 Oct 2026)":
            "https://dabafinance.com/en/dangote-ipo",
        "Reuters: SEC approves ~$1.6bn IPO (4 Sep 2026)":
            "https://www.reuters.com/business/energy/nigerias-dangote-refinery-ipo-raise-between-155-18-bln-sources-2026-09-04/",
        "CNBC Africa: IPO documents signed, 4.1bn shares at N525 (8 Sep 2026)":
            "https://www.cnbcafrica.com/2026/nigerias-dangote-oil-refinery-signs-ipo-documents-before-landmark-share-sale",
        "Dangote Petroleum Refinery Public Offer page":
            "https://ipo.dangote.com/",
    },
    "cement": {
        "Proshare: Dangote Cement FY 2025 deep dive (Mar 2026)":
            "https://proshare.co/articles/dangote-cement-fy-2025-debt-halved-profit-doubled-as-deleveraging-delivers-nigerias-first-trillion-naira-cement-earnings",
        "Business Insider Africa: record $730m profit (Mar 2026)":
            "https://africa.businessinsider.com/local/markets/dangote-cement-reports-record-dollar730m-profit-in-2025-accelerates-pan-african/4ddsn2l",
    },
    "sugar": {
        "NairaMetrics: FY 2025 revenue N829.21bn (Mar 2026)":
            "https://nairametrics.com/2026/03/04/dangote-sugar-narrows-2025-losses-as-50kg-sales-hit-n807-billion-lagos-leads/",
        "Proshare: Dangote Sugar FY 2025 review":
            "https://proshare.co/articles/dangote-sugar-plc-fy-2025-revenue-growth-margin-recovery-and-the-prolonged-journey-back-to-stability",
        "Dangote Sugar FY 2025 audited accounts (3 Mar 2026)":
            "https://sugar.dangote.com/wp-content/uploads/2026/03/DSR-Plc-FY-2025-Accounts.pdf",
    },
    "refinery": {
        "Nigeria Housing Market: refinery rebounds from ~$2bn of losses to $1.82bn H1 2026 profit (Sep 2026)":
            "https://www.nigeriahousingmarket.com/news/dangote-refinery-1-82bn-profit-two-year-loss",
    },
}


def entry_market_cap_usd_bn() -> float:
    """Market cap at the N525 offer price, total shares, at the prospectus FX."""
    return TOTAL_SHARES_BN * OFFER_PRICE_NGN / FX_AT_OFFER


def entry_market_cap_ngn_trn() -> float:
    # total shares are in billions, so billions x N/share = N billion; / 1000 -> N trillion
    return TOTAL_SHARES_BN * OFFER_PRICE_NGN / 1_000


if __name__ == "__main__":
    print(f"Implied market cap at offer: N{entry_market_cap_ngn_trn():.2f}tn "
          f"({entry_market_cap_usd_bn():.1f} $bn at N{FX_AT_OFFER:,.1f}/USD)")
    print(f"H1 2026 net margin: {REFINERY['h1_2026_net_margin']:.1%}, "
          f"annualised net income ${REFINERY['annualised_net_income_usd_bn']:.1f}bn")
    print(f"Cement benchmark: {DANGOTE_CEMENT['net_margin_2025']:.1%} net margin, "
          f"P/E {DANGOTE_CEMENT['pe_2026']}, ROE {DANGOTE_CEMENT['roe_2025']:.1%}")
    print(f"Sugar benchmark: {DANGOTE_SUGAR['net_margin_2025']:.1%} net margin")
