# ⛽ Dangote Refinery IPO — ROI Predictor

Scenario model that projects the **return on investment** for the
**Dangote Petroleum Refinery & Petrochemicals** public offer (₦525/share,
NGX, offer open 14 Sep – 27 Oct 2026) — built from the audited FY2025 numbers
of its sister companies, **Dangote Cement** and **Dangote Sugar**, plus the
refinery's own H1 2026 results.

Companion project to [`Fake-News-`](https://github.com/Teninlanimi/Fake-News-)
(same structure: transparent Python engine + Flask dashboard + About page).

---

## Why sister-company data?

The refinery only has **one half-year of profit history** (it lost $1.51bn in
2024 and $476m in 2025 before earning $1.8bn in H1 2026), so there is nothing
long enough to extrapolate from directly. But two Dangote refineries with
multi-year listed track records trade on the same exchange, under the same
management, exposed to the same naira:

| Benchmark | FY2025 reality | Role in the model |
|---|---|---|
| **Dangote Cement** (N4.31trn revenue, N1.01trn profit, 23.6% net margin, 42.3% ROE, trades at 13.5× P/E) | pricing power + deleveraging worked | **Bull case** |
| **The refinery itself** (H1 2026: 12.5% net margin, ~$3.6bn annualised profit) | current run-rate | **Base case** |
| **Dangote Sugar** (N829bn revenue but a N64.1bn *loss*, −7.7% net margin, N175bn finance costs) | FX + debt can eat a whole margin | **Bear case** |

A key check the data gives us: at ₦525 the offer implies roughly **13.4× the
refinery's annualised H1 2026 profit — almost exactly Dangote Cement's 13.5×**.
The public-offer price already assumes cement-level confidence in a business
with two loss years and $3.65bn of debt. That single fact frames the whole
risk/reward question.

## Results (3-year horizon, naira depreciating 8%/yr)

| Scenario (25% / 50% / 25% weights) | Fair price | ROI (₦) | ROI (USD) |
|---|---|---|---|
| Bull — cement-like execution | ₦1,545 | **+208%** | +145% |
| Base — H1 2026 run-rate holds | ₦716 | **+42%** | +13% |
| Bear — sugar-like margin stress | ₦158 | **−70%** | −76% |
| **Probability-weighted expected** | — | **≈ +55%** (≈ +16%/yr) | ≈ +23% |

Read the shape, not the decimal: the *naira* upside is dominated by earnings
growth + naira depreciation; the *USD* numbers are the truer sense of the
fundamentals; and the bear case is shaped like Dangote Sugar — currencies and
finance costs, not refining, are what break Dangote-linked equities.

## Fair value formula

```
fair_value/share = net income $bn × P/E ÷ 120.13bn shares        (in USD)
roi               = (exit value + dividends − ₦525) ÷ ₦525        (in naira, via FX)
expected ROI      = Σ weight × scenario ROI
```

## Run it

```bat
py model.py            :: scenario report + sensitivity grid -> outputs/
py app.py              :: dashboard at http://127.0.0.1:5000
```

(or double-click `run_app.bat`). Requires Python 3.10+ and Flask
(`py -m pip install -r requirements.txt`).

The dashboard sliders: revenue ($bn), net margin (%), P/E (×), earnings
growth (%/yr), naira depreciation (%/yr), dividend payout (%), and a 1- or
3-year horizon — recomputing fair value and ROI live next to the three presets.
Below the results, a diverging bar chart compares **naira vs USD ROI for every
scenario across 1-, 2- and 3-year holds** on your current levers.

## Project layout

```
data/company_data.py    all verified facts + source URLs (the single source of truth)
model.py                scenario engine, sensitivity grid, markdown report
app.py + templates/     Flask dashboard
outputs/                generated: scenario_report.md, sensitivity_pe_margin.csv
```

## What it can't do (the honest list)

- No greenshoe (up to +30% shares), lock-up-expiry, or oversubscription dynamics
- No tax, crude-supply, petchem-segment, or cash-remittance modelling
- The "dividends in dollars" promise is still pending formal sign-off
- Linear margin×P/E ladder — markets don't behave linearly
- **Educational scenario analysis, not investment advice.** Read the
  [prospectus](https://ipo.dangote.com/) before you commit money.

## Sources

- [Daba Research — live, verified IPO tracker (13 Oct 2026)](https://dabafinance.com/en/dangote-ipo)
- [Reuters — SEC approves ~$1.6bn IPO](https://www.reuters.com/business/energy/nigerias-dangote-refinery-ipo-raise-between-155-18-bln-sources-2026-09-04/)
- [Proshare — Dangote Cement FY2025 deep dive](https://proshare.co/articles/dangote-cement-fy-2025-debt-halved-profit-doubled-as-deleveraging-delivers-nigerias-first-trillion-naira-cement-earnings)
- [NairaMetrics — Dangote Sugar FY2025: revenue ₦829bn](https://nairametrics.com/2026/03/04/dangote-sugar-narrows-2025-losses-as-50kg-sales-hit-n807-billion-lagos-leads/)
- [Dangote Sugar FY2025 audited accounts](https://sugar.dangote.com/wp-content/uploads/2026/03/DSR-Plc-FY-2025-Accounts.pdf)
- [Dangote Petro Refinery offer page](https://ipo.dangote.com/)
