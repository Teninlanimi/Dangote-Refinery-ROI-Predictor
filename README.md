# ⛽ Dangote Refinery IPO — ROI Predictor

Scenario model that projects the **return on investment** for the
**Dangote Petroleum Refinery & Petrochemicals** public offer (₦525/share,
NGX, offer open 14 Sep – 27 Oct 2026) — built from the audited FY2025 numbers
of its sister companies, **Dangote Cement** and **Dangote Sugar**, plus the
refinery's own H1 2026 results.

**Now a production data product:** crude oil, petrol and diesel prices and
the naira exchange rate are pulled on a schedule, validated, stored in PostgreSQL, and fed into
the model; the site runs free on Render + Neon with the pipeline on GitHub Actions
([free deploy](deploy/FREE_DEPLOY.md)), and the full stack is Docker-ready for
AWS ([AWS guide](deploy/AWS_DEPLOY.md)).

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

## Live data pipeline

```
FRED: Brent, petrol, diesel ─┐                     ┌──> market_observations
                             ├─> fetch ─> checks ──┤──> ingestion_runs
open.er-api: USD/NGN ────────┘   (scheduler,       └──> check_results
                                  06:05 & 18:05 UTC)          │
                                                              ▼
                                  3-2-1 crack spread ─> ROI model in live mode
```

**How live data changes the model** (toggle on the dashboard):

1. **Exchange rate.** Exit value in naira is projected from *today's* USD/NGN
   instead of the prospectus rate (₦1,312.5). Your entry cost stays ₦525 at the
   offer rate, so naira weakness since the offer shows up in naira ROI.
2. **Crude.** Revenue is scaled by *latest Brent ÷ average Brent over H1 2026*,
   the half-year the $28.8bn run-rate comes from. Net margin stays a % of
   revenue. The H1 2026 average is computed from the stored history, not typed in.
3. **Crack spread → margin.** A refinery earns the gap between product prices
   and crude, not the crude price. The pipeline computes the industry-standard
   **3-2-1 crack spread** daily: (2 barrels of petrol + 1 barrel of diesel − 3
   barrels of Brent) ÷ 3, using New York Harbor spot prices. Net margin then
   moves with *today's spread ÷ its H1 2026 average*, using only the refinery's
   reported H1 2026 figures (annualised):

   ```
   gross profit  $5.2bn  x spread ratio       (refining margin scales with the spread)
   other costs   $1.6bn  held fixed            (= gross profit − net income: opex, interest, tax)
   live margin = (5.2 x spread ratio − 1.6) ÷ (28.8 x crude factor)
   shift       = live margin − 12.5%           applied to every scenario, capped at ±10 pts
   ```

   So dearer crude with an unchanged spread *lowers* the margin % and leaves
   profit roughly flat, while a wider spread lifts profit. Using the ratio
   rather than the level means the gap between New York Harbor and West
   African prices largely cancels out.

**Data checks** run before anything is stored: values outside a plausible
band are rejected (`range`), large day-to-day moves are stored but flagged
(`jump`), stale sources are flagged (`freshness`), and source outages are
logged (`fetch`). One failing source never blocks the other. Every run and
check is visible at `/status`.

| Endpoint | What it returns |
|---|---|
| `/` | Market: the offer in one sentence, today's oil prices, refining margin and naira rate, price history charts, and what they change in the model |
| `/calculator` | Estimate returns: levers, your result against the three scenarios, return by holding period |
| `/status` | Data pipeline: every run and data-check outcome |
| `/about` | Method: how the estimate is built and what it leaves out |
| `/download/prices.csv` | every stored day: Brent, petrol, diesel, 3-2-1 crack spread, naira rate |
| `/download/pipeline-runs.csv`, `/download/data-checks.csv` | the full pipeline and data-check log |
| `/api/market?days=180` | latest values + history as JSON |
| `/health` | app + database + data freshness (used by Docker) |
| `POST /admin/ingest` | run the pipeline now (needs `X-Ingest-Token`) |

**Usage limits** (per visitor address, via Flask-Limiter): CSV downloads 30 an
hour, `/api/market` 60 an hour, the calculator 300 a minute, `/admin/ingest` 5 an
hour. Over the limit you get HTTP 429 with a plain message. Counters are kept in
each server process's memory, which is enough to stop one visitor hammering a
free server; a multi-server deployment would point `storage_uri` at Redis.
Behind a proxy (Render, Caddy) set `TRUST_PROXY=1` so limits apply to the real
visitor address; it's already set in `render.yaml` and `docker-compose.yml`.

## Run it locally

```bat
py -m pip install -r requirements-dev.txt
copy .env.example .env      :: then paste your free FRED_API_KEY into .env
py -m pipeline.ingest       :: pull crude + FX into instance\market.db (or run_ingest.bat)
py app.py                   :: dashboard at http://127.0.0.1:5000 (or run_app.bat)
py -m pytest -q             :: 33 tests: checks, sources, pipeline, crack spread, downloads, limits, app
py model.py                 :: offline scenario report + sensitivity grid -> outputs/
```

Locally the database is a SQLite file; in production it is PostgreSQL. Only
`DATABASE_URL` changes. Without any data the app still works in static mode
(offer-date figures), exactly as before.

## Deploy

Two documented routes, same code:

- **Free, always on (live site):** Neon Postgres + GitHub Actions running the
  pipeline twice a day + Render hosting the website.
  **[deploy/FREE_DEPLOY.md](deploy/FREE_DEPLOY.md)**
- **AWS (Docker):** `docker compose up -d --build` starts PostgreSQL, the web
  app, the scheduler and Caddy (HTTPS) on one EC2 server.
  **[deploy/AWS_DEPLOY.md](deploy/AWS_DEPLOY.md)** CI (GitHub
Actions) runs the tests on SQLite and PostgreSQL and builds the Docker image on
every push.

The dashboard sliders: revenue ($bn), net margin (%), P/E (×), earnings
growth (%/yr), naira depreciation (%/yr), dividend payout (%), and a 1- or
3-year horizon — recomputing fair value and ROI live next to the three presets.
Below the results, a diverging bar chart compares **naira vs USD ROI for every
scenario across 1-, 2- and 3-year holds** on your current levers.

## Project layout

```
data/company_data.py    all verified facts + source URLs (the single source of truth)
model.py                scenario engine, sensitivity grid, markdown report
app.py + templates/     Flask app: Market, Estimate returns, Data pipeline, Method pages; JSON API; health check
static/                 stylesheet, small SVG chart script, self-hosted Archivo font (SIL OFL)
config.py               settings from environment variables / .env
pipeline/
  sources.py            fetchers: FRED (Brent, petrol, diesel), open.er-api (USD/NGN)
  checks.py             range / jump / freshness rules
  ingest.py             one run: fetch -> check -> store -> log
  scheduler.py          runs ingest on a schedule (separate process)
  market.py             read helpers: latest, history, crude factor, crack spread, FX trend
  db.py                 SQLAlchemy tables (SQLite locally, PostgreSQL in prod)
tests/                  pytest suite (no network needed)
Dockerfile, docker-compose.yml, deploy/   Docker stack, free + AWS deploy guides
.github/workflows/      ci.yml (tests + Docker build), ingest.yml (scheduled pipeline)
render.yaml             Render blueprint for the free web service
outputs/                generated: scenario_report.md, sensitivity_pe_margin.csv
```

## What it can't do (the honest list)

- No greenshoe (up to +30% shares), lock-up-expiry, or oversubscription dynamics
- No tax, crude-supply, petchem-segment, or cash-remittance modelling
- The "dividends in dollars" promise is still pending formal sign-off
- Linear margin×P/E ladder — markets don't behave linearly
- The crack spread uses US (New York Harbor) product prices as a proxy for the
  Atlantic-basin market Dangote sells into, and a 3-2-1 yield, not Dangote's
  actual product slate (which also includes jet fuel, LPG and polypropylene)
- It assumes gross profit moves in proportion to the spread and other costs stay
  fixed in dollars; Nigerian pump-price pressure on how much of the spread
  Dangote keeps is not modelled
- The free FX feed is a market mid-rate; Nigeria's official and parallel rates
  can differ, and it has no history, so FX history builds up from the first run
- **Educational scenario analysis, not investment advice.** Read the
  [prospectus](https://ipo.dangote.com/) before you commit money.

## Sources

Live data (US EIA spot prices via FRED): [Brent crude (DCOILBRENTEU)](https://fred.stlouisfed.org/series/DCOILBRENTEU) ·
[NY Harbor conventional petrol (DGASNYH)](https://fred.stlouisfed.org/series/DGASNYH) ·
[NY Harbor ultra-low-sulfur diesel (DDFUELNYH)](https://fred.stlouisfed.org/series/DDFUELNYH) ·
[Rates By Exchange Rate API](https://www.exchangerate-api.com)

Company data:

- [Daba Research — live, verified IPO tracker (13 Oct 2026)](https://dabafinance.com/en/dangote-ipo)
- [Reuters — SEC approves ~$1.6bn IPO](https://www.reuters.com/business/energy/nigerias-dangote-refinery-ipo-raise-between-155-18-bln-sources-2026-09-04/)
- [Proshare — Dangote Cement FY2025 deep dive](https://proshare.co/articles/dangote-cement-fy-2025-debt-halved-profit-doubled-as-deleveraging-delivers-nigerias-first-trillion-naira-cement-earnings)
- [NairaMetrics — Dangote Sugar FY2025: revenue ₦829bn](https://nairametrics.com/2026/03/04/dangote-sugar-narrows-2025-losses-as-50kg-sales-hit-n807-billion-lagos-leads/)
- [Dangote Sugar FY2025 audited accounts](https://sugar.dangote.com/wp-content/uploads/2026/03/DSR-Plc-FY-2025-Accounts.pdf)
- [Dangote Petro Refinery offer page](https://ipo.dangote.com/)
