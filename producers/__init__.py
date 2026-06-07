"""Producers — the ingestion layer of the Job Market Tracker.

Each producer scrapes one job board and emits records in a single uniform
*contract* (see :mod:`producers.contract`). Raw output is written to
``data/raw/<source>/<date>/jobs_<run_id>.json`` (the Bronze layer).

Public API:

    from producers.registry import get_producer, all_producer_names
    from producers.runner import run_producers
"""

from producers.contract import build_record, CONTRACT_FIELDS  # noqa: F401
from producers.base import BaseProducer  # noqa: F401
