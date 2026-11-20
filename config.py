"""
Runtime settings, read from environment variables (or a local .env file).

Locally nothing needs setting: the app falls back to a SQLite file in
instance/. In production (AWS) the variables come from the .env file next to
docker-compose.yml.
"""

import os

try:  # optional: lets you keep settings in a .env file during development
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_SQLITE = "sqlite:///" + os.path.join(BASE_DIR, "instance", "market.db").replace("\\", "/")

# SQLite locally, PostgreSQL in production, e.g.
#   postgresql+psycopg://roi:password@db:5432/roi
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_SQLITE)

# Free key from https://fred.stlouisfed.org/docs/api/api_key.html (Brent prices)
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# Protects POST /admin/ingest. Leave empty to switch that endpoint off.
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "")

# Hours of the day (UTC) at which the scheduler pulls fresh data.
SCHEDULE_HOURS_UTC = os.getenv("SCHEDULE_HOURS_UTC", "6,18")

# First date to backfill Brent history from (needed for the H1 2026 reference).
BACKFILL_START = os.getenv("BACKFILL_START", "2026-01-01")

HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "20"))
