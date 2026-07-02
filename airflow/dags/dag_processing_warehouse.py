"""DAG 2 — Processing & Warehouse (Silver + Gold layers).

Triggered by job_market_ingestion, not on its own schedule. Runs:
  1. `python -m processing.main`            (Bronze -> Silver, manifest-based)
  2. `python -m warehouse.load_to_postgres` (Silver -> Postgres star schema)

NOTE: the load step deliberately omits `--init`. Schema creation is a
one-time manual step (see project README) — scheduled runs only need
incremental loading, which is safe to re-run (upserts on job_hash, and
etl_load_log skips files already loaded).

On success, triggers the dbt analytics DAG.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.docker.operators.docker import DockerOperator

from _common import COMMON_ENV, DEFAULT_ARGS, DOCKER_TASK_KWARGS

with DAG(
    dag_id="job_market_processing_warehouse",
    default_args=DEFAULT_ARGS,
    description="Clean raw data (Silver) and load it into the PostgreSQL warehouse (Gold)",
    schedule=None,  # triggered by job_market_ingestion
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["job-market-tracker", "processing", "warehouse"],
) as dag:

    clean = DockerOperator(
        task_id="clean_bronze_to_silver",
        command=["python", "-m", "processing.main"],
        environment=COMMON_ENV,
        **DOCKER_TASK_KWARGS,
    )

    load = DockerOperator(
        task_id="load_silver_to_postgres",
        command=["python", "-m", "warehouse.load_to_postgres"],
        environment=COMMON_ENV,
        **DOCKER_TASK_KWARGS,
    )

    trigger_dbt = TriggerDagRunOperator(
        task_id="trigger_dbt_analytics",
        trigger_dag_id="job_market_dbt_analytics",
        wait_for_completion=False,
    )

    clean >> load >> trigger_dbt
