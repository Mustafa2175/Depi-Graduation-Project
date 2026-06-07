"""CLI entry point to run one, several, or all producers.

Usage:
    python -m producers.runner                 # run all (browser ones skip if no browser)
    python -m producers.runner wuzzuf forasna  # run a subset
    python -m producers.runner --list          # list known producers
    PRODUCERS=wuzzuf,bayt python -m producers.runner

Browser-based producers that can't start (no Chrome / no display / missing
dep) are skipped with a warning rather than failing the whole run.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from producers.browser import BrowserUnavailable
from producers.config import get_config
from producers.ingestion_log import record_run
from producers.registry import all_producer_names, get_producer


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _selected(argv_sources: list[str]) -> list[str]:
    if argv_sources:
        return argv_sources
    env = os.getenv("PRODUCERS", "").strip()
    if env:
        return [s.strip() for s in env.replace(",", " ").split() if s.strip()]
    return all_producer_names()


def run_producers(sources: list[str]) -> dict[str, str]:
    """Run the given producers; return {source: status}."""
    config = get_config()
    results: dict[str, str] = {}
    log = logging.getLogger("producers.runner")

    for name in sources:
        try:
            producer = get_producer(name, config)
        except KeyError as exc:
            log.error("%s", exc)
            results[name] = "unknown"
            continue
        try:
            path = producer.run()
            results[name] = f"ok -> {path}" if path else "ok (0 new records)"
        except BrowserUnavailable as exc:
            log.warning("skipping %s: %s", name, exc)
            results[name] = f"skipped ({exc})"
            record_run(config, source=name, run_id=getattr(producer, "run_id", ""),
                       status="skipped", detail=str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("%s failed", name)
            results[name] = f"error ({type(exc).__name__}: {exc})"
            record_run(config, source=name, run_id=getattr(producer, "run_id", ""),
                       status="error", detail=f"{type(exc).__name__}: {exc}")
    return results


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description="Run job-board producers.")
    parser.add_argument("sources", nargs="*", help="producer names (default: all)")
    parser.add_argument("--list", action="store_true", help="list known producers and exit")
    args = parser.parse_args(argv)

    if args.list:
        print("Known producers:", ", ".join(all_producer_names()))
        return 0

    sources = _selected(args.sources)
    results = run_producers(sources)

    print("\n=== Producer run summary ===")
    failures = 0
    for name, status in results.items():
        marker = "✅" if status.startswith("ok") else ("⏭️ " if status.startswith("skipped") else "❌")
        if status.startswith(("error", "unknown")):
            failures += 1
        print(f"  {marker} {name}: {status}")
    # skips/0-records are not hard failures; only real errors are.
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
