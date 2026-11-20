"""
One pipeline run: fetch every series -> check each value -> store what passes,
and log the run plus every check outcome.

Run by hand:     py -m pipeline.ingest
Run on schedule: pipeline/scheduler.py (Docker "scheduler" service on AWS)

The first run for a series backfills from BACKFILL_START; later runs re-read
the last week (to pick up late revisions) and skip dates already stored.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func, insert, select, update

import config
from pipeline import checks, db
from pipeline.sources import FETCHERS, SourceError

T_OBS, T_RUNS, T_CHECKS = db.market_observations, db.ingestion_runs, db.check_results


def _since(conn, series: str) -> date:
    last = conn.execute(select(func.max(T_OBS.c.observed_on))
                        .where(T_OBS.c.series == series)).scalar()
    if last is None:
        return date.fromisoformat(config.BACKFILL_START)
    return last - timedelta(days=7)


def _previous_value(conn, series: str, before: date):
    return conn.execute(
        select(T_OBS.c.value)
        .where(T_OBS.c.series == series, T_OBS.c.observed_on < before)
        .order_by(T_OBS.c.observed_on.desc()).limit(1)
    ).scalar()


def _log(conn, run_id, result: checks.CheckResult):
    conn.execute(insert(T_CHECKS).values(
        run_id=run_id, series=result.series, check_name=result.check_name,
        outcome=result.outcome, detail=result.detail, checked_at=db.utcnow()))


def ingest_series(conn, run_id: int, series: str, fetcher, today: date) -> dict:
    """Fetch, check and store one series. Returns a small summary dict."""
    try:
        observations = fetcher(_since(conn, series))
    except SourceError as exc:
        _log(conn, run_id, checks.CheckResult(series, "fetch", "fail", str(exc)))
        return {"series": series, "fetched": 0, "inserted": 0, "rejected": 0,
                "warned": 0, "ok": False, "error": str(exc)}

    if not observations:
        _log(conn, run_id, checks.CheckResult(series, "fetch", "fail", "source returned no rows"))
        return {"series": series, "fetched": 0, "inserted": 0, "rejected": 0,
                "warned": 0, "ok": False, "error": "no rows"}

    observations = sorted(observations, key=lambda o: o.observed_on)
    existing = set(conn.execute(
        select(T_OBS.c.observed_on).where(
            T_OBS.c.series == series,
            T_OBS.c.observed_on >= observations[0].observed_on)
    ).scalars())

    counts = Counter()
    previous = None
    for obs in observations:
        if obs.observed_on in existing:
            counts["duplicate"] += 1
            continue
        if previous is None:
            previous = _previous_value(conn, series, obs.observed_on)

        rng = checks.check_range(series, obs.value)
        if rng.outcome == "fail":
            rng.detail = f"{obs.observed_on}: {rng.detail}"
            _log(conn, run_id, rng)
            counts["rejected"] += 1
            continue

        jump = checks.check_jump(series, obs.value, previous)
        quality = "ok"
        if jump.outcome == "warn":
            jump.detail = f"{obs.observed_on}: {jump.detail}"
            _log(conn, run_id, jump)
            quality = "warn"
            counts["warned"] += 1

        conn.execute(insert(T_OBS).values(
            series=series, observed_on=obs.observed_on, value=obs.value,
            source=obs.source, quality=quality, fetched_at=db.utcnow(), run_id=run_id))
        existing.add(obs.observed_on)
        previous = obs.value
        counts["inserted"] += 1

    # One summary line per run so the status page shows checks ran even when all pass
    _log(conn, run_id, checks.CheckResult(
        series, "range", "pass" if not counts["rejected"] else "fail",
        f"{counts['inserted']} new row(s) accepted, {counts['rejected']} rejected, "
        f"{counts['duplicate']} already stored"))
    _log(conn, run_id, checks.check_freshness(series, observations[-1].observed_on, today))

    return {"series": series, "fetched": len(observations), "inserted": counts["inserted"],
            "rejected": counts["rejected"], "warned": counts["warned"],
            "ok": counts["rejected"] == 0}


def run(url: str = None, fetchers: dict = None, today: date = None) -> dict:
    """Execute one full pipeline run and return its summary."""
    engine = db.init_db(url)
    fetchers = fetchers or FETCHERS
    today = today or db.utcnow().date()

    with engine.begin() as conn:
        run_id = conn.execute(insert(T_RUNS).values(
            started_at=db.utcnow(), status="running", rows_inserted=0)).inserted_primary_key[0]

    summaries = []
    for series, fetcher in fetchers.items():
        # each series in its own transaction: one bad source can't roll back the other
        with engine.begin() as conn:
            summaries.append(ingest_series(conn, run_id, series, fetcher, today))

    n_ok = sum(s["ok"] for s in summaries)
    status = "success" if n_ok == len(summaries) else ("failed" if n_ok == 0 and
             not any(s["inserted"] for s in summaries) else "partial")
    inserted = sum(s["inserted"] for s in summaries)
    message = "; ".join(
        f"{s['series']}: +{s['inserted']}" + (f" ({s['error']})" if s.get("error") else "")
        for s in summaries)

    with engine.begin() as conn:
        conn.execute(update(T_RUNS).where(T_RUNS.c.id == run_id).values(
            finished_at=db.utcnow(), status=status, rows_inserted=inserted, message=message))

    return {"run_id": run_id, "status": status, "rows_inserted": inserted, "series": summaries}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pull crude + FX data into the database")
    ap.add_argument("--only", choices=sorted(FETCHERS), help="run a single series")
    args = ap.parse_args(argv)
    fetchers = {args.only: FETCHERS[args.only]} if args.only else None
    result = run(fetchers=fetchers)
    print(json.dumps(result, indent=2, default=str))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
