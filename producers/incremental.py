"""Fetch-time incremental marker.

Keeps a per-source set of job ids already emitted in previous runs
(``<meta>/seen/<source>.json``) so a producer can drop postings it has
already collected and emit only *new* ones each run. Controlled by the
``INCREMENTAL`` setting (on by default); disable with ``INCREMENTAL=0`` for a
full re-scrape.
"""
from __future__ import annotations

import json

from producers.config import Config


class SeenStore:
    def __init__(self, config: Config, source: str):
        self._path = config.meta_dir() / "seen" / f"{source}.json"
        self._seen: set[str] = self._load()

    def _load(self) -> set[str]:
        if self._path.exists():
            try:
                return set(json.loads(self._path.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                return set()
        return set()

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._seen

    def add_many(self, job_ids) -> None:
        self._seen.update(job_ids)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(sorted(self._seen), ensure_ascii=False), encoding="utf-8"
        )
