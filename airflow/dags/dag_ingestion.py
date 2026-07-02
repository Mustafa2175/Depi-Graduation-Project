"""DAG 1 — Ingestion (Bronze layer).

Runs each producer (Wuzzuf, Forasna, Jobzella, Bayt, Indeed) as its own
parallel task via `python -m producers.runner <source>`, exactly like you'd
run manually. On success, triggers the processing/warehouse DAG.

Schedule: every 6 hours, per the project plan's automation design.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.docker.operators.docker import DockerOperator

from _common import COMMON_ENV, DEFAULT_ARGS, DOCKER_TASK_KWARGS

PRODUCERS = ["wuzzuf", "forasna", "jobzella", "bayt", "indeed"]

with DAG(
    dag_id="job_market_ingestion",
    default_args=DEFAULT_ARGS,
    description="Scrape raw job postings from each source into the Bronze layer",
    schedule="0 */6 * * *",  # every 6 hours
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["job-market-tracker", "ingestion"],
) as dag:

    ingestion_tasks = [
        DockerOperator(
            task_id=f"ingest_{source}",
            command=["python", "-m", "producers.runner", source],
            environment=COMMON_ENV,
            **DOCKER_TASK_KWARGS,
        )
        for source in PRODUCERS
    ]

    trigger_processing = TriggerDagRunOperator(
        task_id="trigger_processing_warehouse",
        trigger_dag_id="job_market_processing_warehouse",
        wait_for_completion=False,
    )

    ingestion_tasks >> trigger_processing
