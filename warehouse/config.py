"""Database configuration for the warehouse loader and dbt.

Reads connection settings from the environment (so nothing is hardcoded and
the same config works on any machine). Values come from a project-root `.env`
file (auto-loaded if python-dotenv is installed) or real environment
variables, falling back to the defaults shipped in `.env.example`.

All accessors read the environment *live* on each call, so tests can switch
to an isolated database/workspace at runtime (see warehouse/isolation.py)
without import-order gymnastics.
"""
import os

# Auto-load a project-root .env so `python warehouse/...` works without the
# caller having to export variables. Harmless if python-dotenv isn't present.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def db_config() -> dict:
    return {
        "host":     os.getenv("PGHOST", "localhost"),
        "port":     int(os.getenv("PGPORT", "5432")),
        "user":     os.getenv("PGUSER", "jobmarket"),
        "password": os.getenv("PGPASSWORD", "jobmarket"),
        "dbname":   os.getenv("PGDATABASE", "job_market_tracker"),
    }


def silver_dir() -> str:
    """Where the Silver (cleaned CSV) layer lives, relative to project root."""
    return os.getenv("SILVER_DIR", "data/silver")


def sqlalchemy_url() -> str:
    c = db_config()
    auth = c["user"]
    if c["password"]:
        auth = f'{c["user"]}:{c["password"]}'
    return f'postgresql+psycopg2://{auth}@{c["host"]}:{c["port"]}/{c["dbname"]}'


def psycopg2_dsn() -> dict:
    """Kwargs for psycopg2.connect()."""
    c = db_config()
    if not c["password"]:
        c.pop("password")  # let libpq use peer/trust auth when no password set
    return c
