import config


def test_provider_urls_use_psycopg_driver():
    n = config._normalise_db_url
    neon = "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert n(neon) == "postgresql+psycopg://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    assert n("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert n("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert n("sqlite:///x.db") == "sqlite:///x.db"
