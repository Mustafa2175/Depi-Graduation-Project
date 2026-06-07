"""Central, environment-driven configuration for all producers.

Nothing here is hardcoded to a machine: every path and tunable can be
overridden with an environment variable (or a ``.env`` file, which is loaded
automatically if python-dotenv is installed). Sensible defaults let the
package run out of the box on any device.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional: load .env if present, but never required
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _project_root() -> Path:
    # producers/config.py -> producers/ -> project root
    return Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _which(*candidates: str) -> str:
    """Return the first candidate that exists on PATH or as an absolute path."""
    for cand in candidates:
        if not cand:
            continue
        if os.path.isabs(cand) and os.path.exists(cand):
            return cand
        found = shutil.which(cand)
        if found:
            return found
    return ""


@dataclass(frozen=True)
class Config:
    # ── Storage ──────────────────────────────────────────────
    raw_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("RAW_DIR", str(_project_root() / "data" / "raw"))
        )
    )

    # ── Search scope ─────────────────────────────────────────
    job_query: str = field(default_factory=lambda: os.getenv("JOB_QUERY", ""))
    # Per-run volume caps (keep small for tests, large for real runs).
    max_jobs: int = field(default_factory=lambda: _env_int("MAX_JOBS", 300))
    max_pages: int = field(default_factory=lambda: _env_int("MAX_PAGES", 20))
    # Incremental ingestion: emit only postings not seen in previous runs.
    incremental: bool = field(default_factory=lambda: _env_bool("INCREMENTAL", True))

    # ── HTTP politeness / resilience ─────────────────────────
    rate_limit_seconds: float = field(
        default_factory=lambda: _env_float("HTTP_RATE_LIMIT_SECONDS", 0.7)
    )
    max_retries: int = field(default_factory=lambda: _env_int("HTTP_MAX_RETRIES", 5))
    backoff_factor: float = field(
        default_factory=lambda: _env_float("HTTP_BACKOFF_FACTOR", 0.8)
    )
    request_timeout: int = field(
        default_factory=lambda: _env_int("HTTP_TIMEOUT_SECONDS", 20)
    )
    max_threads: int = field(default_factory=lambda: _env_int("MAX_THREADS", 8))
    user_agent: str = field(
        default_factory=lambda: os.getenv(
            "HTTP_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
    )

    # ── Browser (Selenium / undetected-chromedriver) ─────────
    chrome_binary: str = field(
        default_factory=lambda: _which(
            os.getenv("CHROME_BIN", ""),
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
        )
    )
    chromedriver_binary: str = field(
        default_factory=lambda: _which(os.getenv("CHROMEDRIVER", ""), "chromedriver")
    )
    # Bayt sits behind Cloudflare, which blocks headless; default to headful
    # when a display exists. Override with HEADFUL=0/1.
    headful: bool = field(
        default_factory=lambda: _env_bool(
            "HEADFUL", bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
        )
    )
    browser_wait_seconds: int = field(
        default_factory=lambda: _env_int("BROWSER_WAIT_SECONDS", 8)
    )
    # Optional proxy for sites that block datacenter IPs (e.g. Indeed on CI).
    proxy: str = field(default_factory=lambda: os.getenv("SCRAPER_PROXY", ""))

    def meta_dir(self) -> Path:
        """Directory for pipeline bookkeeping (ingestion log, seen-jobs store)."""
        return Path(os.getenv("META_DIR", str(self.raw_dir.parent / "meta")))

    def run_id(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")


# Singleton-style accessor so callers share one resolved config.
_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config()
    return _CONFIG
