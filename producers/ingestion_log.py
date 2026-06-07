"""Persistent ingestion run log.

Every producer run appends one JSON line to ``<meta>/ingestion_log.jsonl``
recording the source, run id, status, record count, timestamp and output
path — satisfying the Phase 2 requirement to "log each ingestion run with
source, record count, and timestamp".
"""
from __future__ import annotations

import json
from datetime import datetime

from producers.config import Config


def log_path(config: Config):
    return config.meta_dir() / "ingestion_log.jsonl"


def record_run(
    config: Config,
    *,
    source: str,
    run_id: str,
    status: str,
    records: int = 0,
    output_path=None,
    detail: str = "",
) -> dict:
    """Append one ingestion-run entry and return it."""
    path = log_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "run_id": run_id,
        "status": status,                       # ok | empty | skipped | error
        "records": records,
        "output": str(output_path) if output_path else None,
        "detail": detail,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
