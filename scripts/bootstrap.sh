#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Idempotent end-to-end bootstrap: wait for Postgres -> ensure database ->
# build warehouse schema + load data -> run dbt.
#
# Safe to run repeatedly (every step is upsert/IF-NOT-EXISTS based).
# Works both inside the Docker `app` container and on a local machine.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT"

# Load .env for local runs, but NEVER override variables already present in the
# environment (e.g. Docker Compose sets PGHOST=db). This keeps a developer's
# local .env from leaking into / breaking the container.
if [ -f .env ] && [ -z "${PGHOST:-}" ]; then set -a; . ./.env; set +a; fi

PGHOST="${PGHOST:-localhost}"; PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-${USER:-postgres}}"; PGDATABASE="${PGDATABASE:-job_market_tracker}"
export PGHOST PGPORT PGUSER PGDATABASE
[ -n "${PGPASSWORD:-}" ] && export PGPASSWORD

# Pick the right binaries. In Docker everything is on PATH (Python 3.12).
# Locally we prefer the dedicated 3.12 virtualenv created by setup_local.sh,
# which holds the app deps and dbt.
if [ -x "$ROOT/.venv/bin/python" ]; then PY_BIN="$ROOT/.venv/bin/python"
else PY_BIN="${PYTHON_BIN:-python3}"; fi
if [ -x "$ROOT/.venv/bin/dbt" ];    then DBT_BIN="$ROOT/.venv/bin/dbt"
elif command -v dbt >/dev/null 2>&1; then DBT_BIN="dbt"
else DBT_BIN=""; fi

echo "==> [1/4] Waiting for PostgreSQL at ${PGHOST}:${PGPORT} ..."
for _ in $(seq 1 30); do
  if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; then break; fi
  sleep 2
done
pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1 \
  || { echo "ERROR: PostgreSQL not reachable at ${PGHOST}:${PGPORT}"; exit 1; }

echo "==> [2/4] Ensuring database '${PGDATABASE}' exists ..."
if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${PGDATABASE}'" | grep -q 1; then
  createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
  echo "    created database '${PGDATABASE}'"
else
  echo "    database already present"
fi

# Generate sample Silver data on first run so a fresh clone has something to
# load (real data comes from `python -m producers.runner` + processing/main.py).
if ! find "${SILVER_DIR:-data/silver}" -name '*.csv' 2>/dev/null | grep -q .; then
  echo "==> [3/4] No Silver data found — generating sample data ..."
  "$PY_BIN" warehouse/make_sample_data.py
else
  echo "==> [3/4] Silver data present — skipping sample generation"
fi

echo "    building warehouse schema + loading ..."
"$PY_BIN" -m warehouse.load_to_postgres --init

echo "==> [4/4] Running dbt (deps + build) ..."
if [ -n "$DBT_BIN" ]; then
  # Always use an ABSOLUTE profiles dir — a relative one (e.g. from .env)
  # breaks once we cd into the project directory.
  export DBT_PROFILES_DIR="$ROOT/dbt/job_market_tracker"
  ( cd dbt/job_market_tracker && "$DBT_BIN" deps && "$DBT_BIN" build )
else
  echo "    dbt not installed — run scripts/setup_local.sh (local) or use Docker."
fi

echo "==> Bootstrap complete."
