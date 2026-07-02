"""DAG 3 — dbt Analytics.

Triggered by job_market_processing_warehouse, not on its own schedule.
Mirrors what scripts/bootstrap.sh does manually:
    cd dbt/job_market_tracker && dbt deps && dbt build

`dbt build` runs models + tests + snapshots + seeds in one dependency-aware
pass, matching your existing bootstrap script. Split into `dbt deps` and
`dbt build` as separate tasks so a dependency-resolution failure is clearly
distinguishable from a model/test failure in the Airflow UI.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator

from _common import COMMON_ENV, DEFAULT_ARGS, DOCKER_TASK_KWARGS

DBT_CMD = "cd dbt/job_market_tracker && {cmd}"

with DAG(
    dag_id="job_market_dbt_analytics",
    default_args=DEFAULT_ARGS,
    description="Run dbt models/tests to build analytics-ready marts",
    schedule=None,  # triggered by job_market_processing_warehouse
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["job-market-tracker", "dbt"],
) as dag:

    dbt_deps = DockerOperator(
        task_id="dbt_deps",
        command=["bash", "-c", DBT_CMD.format(cmd="dbt deps")],
        environment=COMMON_ENV,
        **DOCKER_TASK_KWARGS,
    )

    dbt_build = DockerOperator(
        task_id="dbt_build",
        command=["bash", "-c", DBT_CMD.format(cmd="dbt build")],
        environment=COMMON_ENV,
        **DOCKER_TASK_KWARGS,
    )

    dbt_deps >> dbt_build
