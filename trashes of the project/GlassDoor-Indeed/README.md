# Job Scraper

Scrapes Indeed for tech jobs and saves to JSON. Designed to run as an Airflow DAG or standalone script.

## Structure

- `producers/job_scraper.py`: Core logic using `python-jobspy`.
- `jobs_dag.py`: Airflow DAG definition.
- `requirements.txt`: Python deps.

## How to run

1. Install deps: `pip install -r requirements.txt`
2. Run locally: `python producers/job_scraper.py`
3. Results are saved in the `output/` folder.

## Config

Set these env vars to override defaults:

- `SEARCH_TERMS` (e.g. "python,java")
- `SCRAPE_LOCATION` (e.g. "New York")
- `RESULTS_PER_TERM` (default 50)

## Performance Demo

To see it in action with a quick run:

```bash
export SEARCH_TERMS="python developer"
export RESULTS_PER_TERM=10
python producers/job_scraper.py
```

Check the `output/` folder for the resulting JSON.
