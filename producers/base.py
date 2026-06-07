"""Base class shared by every producer.

A producer's only job is to implement :meth:`fetch`, returning a list of
contract records (use :func:`producers.contract.build_record`). The base
class handles run-id generation, contract validation, intra-run
deduplication, JSON persistence to the Bronze layer, and logging — so the
concrete sources stay small and focused on extraction.
"""
from __future__ import annotations

import abc
import json
import logging
from datetime import datetime
from pathlib import Path

from producers.config import Config, get_config
from producers.contract import CONTRACT_FIELDS, validate_record
from producers.incremental import SeenStore
from producers.ingestion_log import record_run


class BaseProducer(abc.ABC):
    #: short source identifier, e.g. "wuzzuf"; set by subclasses.
    source: str = ""
    #: homepage used as a fallback job_url by the processor when missing.
    home_url: str = ""

    def __init__(self, config: Config | None = None):
        if not self.source:
            raise ValueError(f"{type(self).__name__} must set a `source` name")
        self.config = config or get_config()
        self.run_id = self.config.run_id()
        self.log = logging.getLogger(f"producers.{self.source}")

    # ── to implement ─────────────────────────────────────────
    @abc.abstractmethod
    def fetch(self) -> list[dict]:
        """Scrape and return a list of contract-compliant records."""
        raise NotImplementedError

    # ── orchestration ────────────────────────────────────────
    def run(self) -> Path | None:
        """Fetch, validate, dedupe, (optionally) drop seen, persist, log."""
        self.log.info("starting (run_id=%s)", self.run_id)
        records = self.fetch()

        clean = self._validate_and_dedupe(records)
        if self.config.incremental:
            clean = self._drop_seen(clean)

        if not clean:
            self.log.warning("no new records produced")
            record_run(self.config, source=self.source, run_id=self.run_id,
                       status="empty", records=0)
            return None

        path = self._save(clean)
        self.log.info("saved %d records -> %s", len(clean), path)
        record_run(self.config, source=self.source, run_id=self.run_id,
                   status="ok", records=len(clean), output_path=path)
        return path

    def _drop_seen(self, records: list[dict]) -> list[dict]:
        """Keep only postings not seen in previous runs; persist the new ids."""
        store = SeenStore(self.config, self.source)
        fresh = [r for r in records if r["job_id"] not in store]
        skipped = len(records) - len(fresh)
        if skipped:
            self.log.info("incremental: %d new, %d already seen", len(fresh), skipped)
        if fresh:
            store.add_many(r["job_id"] for r in fresh)
            store.save()
        return fresh

    # ── helpers ──────────────────────────────────────────────
    def _validate_and_dedupe(self, records: list[dict]) -> list[dict]:
        seen: set[str] = set()
        clean: list[dict] = []
        invalid = 0
        for rec in records:
            errors = validate_record(rec)
            if errors:
                invalid += 1
                self.log.debug("dropping invalid record: %s", errors)
                continue
            job_id = rec["job_id"]
            if job_id in seen:
                continue
            seen.add(job_id)
            # enforce canonical key order
            clean.append({k: rec[k] for k in CONTRACT_FIELDS})
        if invalid:
            self.log.warning("dropped %d invalid record(s)", invalid)
        return clean

    def _save(self, records: list[dict]) -> Path:
        run_date = datetime.now().strftime("%Y-%m-%d")
        out_dir = self.config.raw_dir / self.source / run_date
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"jobs_{self.run_id}.json"
        with out_file.open("w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        return out_file
