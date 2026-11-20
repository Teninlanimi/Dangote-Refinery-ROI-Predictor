"""
Data checks run on every fetched observation BEFORE it is stored.

  fail -> the value is rejected (never reaches the database or the model)
  warn -> stored, but flagged quality="warn" and shown on the status page
  pass -> stored as quality="ok"

Checks
  range      value inside a plausible band              (fail outside)
  jump       move vs the previous stored value          (warn if too large)
  freshness  how old the newest observation is          (warn if stale)
  duplicate  same series+date already stored            (skipped, not an error)
"""

from dataclasses import dataclass
from datetime import date

# Plausible bands and tolerances per series. Wide on purpose: they catch
# broken data (0, a price in cents, NGN quoted per EUR...), not market moves.
RULES = {
    "brent_usd": {"min": 10.0, "max": 250.0, "max_jump": 0.15, "max_age_days": 7},
    "usdngn": {"min": 300.0, "max": 5000.0, "max_jump": 0.10, "max_age_days": 4},
    # product prices are USD per gallon (x42 = per barrel)
    "gasoline_nyh": {"min": 0.5, "max": 8.0, "max_jump": 0.20, "max_age_days": 7},
    "diesel_nyh": {"min": 0.5, "max": 8.0, "max_jump": 0.20, "max_age_days": 7},
}


@dataclass
class CheckResult:
    series: str
    check_name: str
    outcome: str     # pass | warn | fail
    detail: str


def check_range(series: str, value: float) -> CheckResult:
    r = RULES[series]
    if value != value:  # NaN
        return CheckResult(series, "range", "fail", "value is NaN")
    if not (r["min"] <= value <= r["max"]):
        return CheckResult(series, "range", "fail",
                           f"{value:,.2f} outside plausible band {r['min']:,.0f}-{r['max']:,.0f}")
    return CheckResult(series, "range", "pass", f"{value:,.2f} within {r['min']:,.0f}-{r['max']:,.0f}")


def check_jump(series: str, value: float, previous: float) -> CheckResult:
    if previous is None or previous == 0:
        return CheckResult(series, "jump", "pass", "no previous value to compare")
    move = value / previous - 1
    limit = RULES[series]["max_jump"]
    if abs(move) > limit:
        return CheckResult(series, "jump", "warn",
                           f"moved {move:+.1%} vs previous {previous:,.2f} (limit ±{limit:.0%})")
    return CheckResult(series, "jump", "pass", f"moved {move:+.1%} vs previous {previous:,.2f}")


def check_freshness(series: str, newest: date, today: date) -> CheckResult:
    age = (today - newest).days
    limit = RULES[series]["max_age_days"]
    if age > limit:
        return CheckResult(series, "freshness", "warn",
                           f"newest observation is {age} days old (limit {limit})")
    return CheckResult(series, "freshness", "pass", f"newest observation is {age} day(s) old")
