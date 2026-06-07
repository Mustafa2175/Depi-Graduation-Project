"""A resilient, polite HTTP session shared by the requests-based producers.

Combines three things every production scraper needs:
* automatic retries with exponential backoff on transient errors / 429s
  (honouring ``Retry-After``),
* a minimum interval between requests (rate limiting), so we don't hammer
  a host and trip its abuse protection,
* sane default headers.
"""
from __future__ import annotations

import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from producers.config import Config


class RateLimitedSession:
    """Wraps :class:`requests.Session` with retries + a min request interval."""

    def __init__(self, config: Config):
        self._config = config
        self._min_interval = max(0.0, config.rate_limit_seconds)
        self._last_request_ts = 0.0
        self._lock = threading.Lock()

        retry = Retry(
            total=config.max_retries,
            connect=config.max_retries,
            read=config.max_retries,
            status=config.max_retries,
            backoff_factor=config.backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=config.max_threads * 2)

        self._session = requests.Session()
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            }
        )
        if config.proxy:
            self._session.proxies.update({"http": config.proxy, "https": config.proxy})

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            elapsed = time.monotonic() - self._last_request_ts
            wait = self._min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request_ts = time.monotonic()

    def get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self._config.request_timeout)
        self._throttle()
        return self._session.get(url, **kwargs)

    @property
    def raw(self) -> requests.Session:
        return self._session

    def close(self) -> None:
        self._session.close()
