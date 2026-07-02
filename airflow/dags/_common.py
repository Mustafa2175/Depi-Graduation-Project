"""Shared constants used by all Job Market Tracker DAGs.

Kept in its own module so the 3 DAG files don't repeat the same env-var
plumbing. Airflow auto-discovers only files that define a DAG, so a plain
helper module like this is safe to drop in dags/ — it won't be picked up
as a DAG itself.
"""
from __future__ import annotations

import os
from datetime import timedelta

from docker.types import Mount

# The pipeline image is your project's own `app` image (built from your
# existing Dockerfile). Airflow never installs pandas/dbt/etc. itself —
# it just launches short-lived containers from this image per task.
PIPELINE_IMAGE = os.getenv("PIPELINE_IMAGE", "jobmarket-pipeline:latest")

# Docker network shared by db / app / airflow, defined in
# docker-compose.airflow.yml. Task containers join this network so they
# can resolve the `db` (Postgres) hostname.
PIPELINE_NETWORK = os.getenv("PIPELINE_NETWORK", "pipeline_net")

# Env vars every pipeline stage needs (matches your app service's env).
COMMON_ENV = {
    "PGHOST": os.getenv("PGHOST", "db"),
    "PGPORT": os.getenv("PGPORT", "5432"),
    "PGUSER": os.getenv("PGUSER", "jobmarket"),
    "PGPASSWORD": os.getenv("PGPASSWORD", "jobmarket"),
    "PGDATABASE": os.getenv("PGDATABASE", "job_market_tracker"),
    "DBT_PROFILES_DIR": "/app/dbt/job_market_tracker",
}

# Same named volume your `app` service uses for /app/data (Bronze/Silver),
# so task containers read/write the exact same files as manual runs.
DATA_MOUNT = [Mount(source="pipeline_data", target="/app/data", type="volume")]

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Common kwargs shared by every DockerOperator task across the 3 DAGs.
DOCKER_TASK_KWARGS = dict(
    image=PIPELINE_IMAGE,
    network_mode=PIPELINE_NETWORK,
    mounts=DATA_MOUNT,
    docker_url="unix://var/run/docker.sock",
    auto_remove="success",  # remove container on success; keep it around on failure for debugging
    mount_tmp_dir=False,
)
