"""
Database layer (SQLAlchemy Core). Same code runs on SQLite locally and
PostgreSQL in production; only DATABASE_URL changes.

Tables
  market_observations  one row per (series, date): the price history
  ingestion_runs       one row per pipeline run: when, status, rows added
  check_results        every data check from every run (pass / warn / fail)
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (Column, Date, DateTime, Float, ForeignKey, Integer,
                        MetaData, String, Table, Text, UniqueConstraint,
                        create_engine)

import config

metadata = MetaData()

market_observations = Table(
    "market_observations", metadata,
    Column("id", Integer, primary_key=True),
    Column("series", String(32), nullable=False, index=True),   # brent_usd | usdngn
    Column("observed_on", Date, nullable=False),
    Column("value", Float, nullable=False),
    Column("source", String(64), nullable=False),
    Column("quality", String(8), nullable=False, default="ok"),  # ok | warn
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Integer, ForeignKey("ingestion_runs.id"), nullable=True),
    UniqueConstraint("series", "observed_on", name="uq_series_date"),
)

ingestion_runs = Table(
    "ingestion_runs", metadata,
    Column("id", Integer, primary_key=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", String(16), nullable=False, default="running"),  # running|success|partial|failed
    Column("rows_inserted", Integer, nullable=False, default=0),
    Column("message", Text),
)

check_results = Table(
    "check_results", metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", Integer, ForeignKey("ingestion_runs.id"), nullable=False, index=True),
    Column("series", String(32), nullable=False),
    Column("check_name", String(32), nullable=False),
    Column("outcome", String(8), nullable=False),   # pass | warn | fail
    Column("detail", Text),
    Column("checked_at", DateTime(timezone=True), nullable=False),
)

_engines = {}


def get_engine(url: str = None):
    """One engine per URL, created lazily (tests pass their own URL)."""
    url = url or config.DATABASE_URL
    if url not in _engines:
        if url.startswith("sqlite:///"):
            path = url.replace("sqlite:///", "", 1)
            if path and path != ":memory:":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        engine = create_engine(url, pool_pre_ping=True, future=True)
        metadata.create_all(engine)       # idempotent: creates missing tables only
        _engines[url] = engine
    return _engines[url]


def init_db(url: str = None):
    """Create the tables if they don't exist yet (safe to call every start)."""
    return get_engine(url)


def utcnow():
    return datetime.now(timezone.utc)
