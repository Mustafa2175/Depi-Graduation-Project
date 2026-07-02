# Canonical, reproducible runtime for the whole pipeline (app + dbt).
# Python 3.12 because dbt does not yet support 3.13/3.14.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    DBT_PROFILES_DIR=/app/dbt/job_market_tracker

WORKDIR /app

# postgresql-client provides pg_isready / psql / createdb used by bootstrap.sh.
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY requirements.txt dbt-requirements.txt ./
RUN pip install -r requirements.txt -r dbt-requirements.txt

COPY . .
RUN sed -i 's/\r$//' scripts/*.sh
RUN chmod +x scripts/*.sh

# Default: wait for DB, build the warehouse, load data, run dbt.
CMD ["./scripts/bootstrap.sh"]
