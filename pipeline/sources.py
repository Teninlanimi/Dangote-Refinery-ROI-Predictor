"""
Where the live numbers come from. Each fetcher returns a list of Observation.

  brent_usd     Brent crude spot, USD/barrel, daily          - FRED DCOILBRENTEU
  gasoline_nyh  Petrol (conventional regular) spot, USD/gal  - FRED DGASNYH
  diesel_nyh    Ultra-low-sulfur diesel spot, USD/gal        - FRED DDFUELNYH
  usdngn        Naira per US dollar, daily                   - open.er-api.com (no key)

The three FRED series are US EIA spot prices republished by the St. Louis Fed
(one free API key covers all of them). Petrol and diesel feed the 3-2-1 crack
spread in pipeline/market.py.

Swap or add a source by writing another function with the same shape and
registering it in FETCHERS.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

import config


@dataclass(frozen=True)
class Observation:
    series: str
    observed_on: date
    value: float
    source: str


class SourceError(RuntimeError):
    """A source could not be reached or returned something unusable."""


FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
ER_API_URL = "https://open.er-api.com/v6/latest/USD"


def _fred(fred_id: str, series: str, since: date, session=None) -> list:
    """Daily observations of one FRED series from `since` onwards."""
    if not config.FRED_API_KEY:
        raise SourceError(f"FRED_API_KEY is not set - {series} skipped")
    http = session or requests
    try:
        resp = http.get(FRED_URL, timeout=config.HTTP_TIMEOUT_S, params={
            "series_id": fred_id,
            "api_key": config.FRED_API_KEY,
            "file_type": "json",
            "observation_start": since.isoformat(),
        })
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise SourceError(f"FRED request for {fred_id} failed: {exc}") from exc

    out = []
    for row in payload.get("observations", []):
        raw = row.get("value")
        if raw in (None, "", "."):      # FRED marks holidays/missing days with "."
            continue
        try:
            out.append(Observation(series, date.fromisoformat(row["date"]),
                                   float(raw), f"FRED:{fred_id}"))
        except (KeyError, ValueError):
            continue
    return out


def fetch_brent(since: date, session=None) -> list:
    """Brent crude, USD per barrel."""
    return _fred("DCOILBRENTEU", "brent_usd", since, session)


def fetch_gasoline(since: date, session=None) -> list:
    """New York Harbor conventional regular petrol, USD per gallon."""
    return _fred("DGASNYH", "gasoline_nyh", since, session)


def fetch_diesel(since: date, session=None) -> list:
    """New York Harbor ultra-low-sulfur No. 2 diesel, USD per gallon."""
    return _fred("DDFUELNYH", "diesel_nyh", since, session)


def fetch_usdngn(since: date = None, session=None) -> list:
    """Latest USD/NGN rate (this free endpoint has no history; we build it daily)."""
    http = session or requests
    try:
        resp = http.get(ER_API_URL, timeout=config.HTTP_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise SourceError(f"open.er-api request failed: {exc}") from exc

    if payload.get("result") != "success":
        raise SourceError(f"open.er-api returned result={payload.get('result')!r}")
    rate = (payload.get("rates") or {}).get("NGN")
    if rate is None:
        raise SourceError("open.er-api response has no NGN rate")
    ts = payload.get("time_last_update_unix")
    observed = (datetime.fromtimestamp(ts, tz=timezone.utc).date()
                if ts else datetime.now(timezone.utc).date())
    return [Observation("usdngn", observed, float(rate), "open.er-api.com")]


FETCHERS = {
    "brent_usd": fetch_brent,
    "gasoline_nyh": fetch_gasoline,
    "diesel_nyh": fetch_diesel,
    "usdngn": fetch_usdngn,
}
