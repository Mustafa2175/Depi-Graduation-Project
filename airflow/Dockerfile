# Airflow orchestration image.
# This image does NOT contain your pipeline code, pandas, dbt, etc. It only
# needs the Docker provider so DAGs can launch short-lived containers from
# your existing `app`/pipeline image (Option A: Airflow orchestrates,
# it doesn't execute pipeline logic itself). This avoids any dependency
# conflicts between Airflow's pinned requirements and your pipeline's.
FROM apache/airflow:2.10.3-python3.12

RUN pip install --no-cache-dir \
    "apache-airflow-providers-docker" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt"
