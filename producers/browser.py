"""Browser helpers for the Selenium / undetected-chromedriver producers.

Everything here is *lazy* and *defensive*: importing this module never
imports Selenium, and constructing a driver fails with a clear
:class:`BrowserUnavailable` instead of a cryptic stack trace when no
Chrome/Chromedriver/display is present. This lets the requests-based
producers (and the whole processing pipeline) run on machines without a
browser, while the browser-based ones degrade gracefully.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile

from producers.config import Config

logger = logging.getLogger("producers.browser")


class BrowserUnavailable(RuntimeError):
    """Raised when a usable Chrome/Chromedriver/display cannot be found."""


def detect_chrome_major(config: Config) -> int | None:
    """Return the installed Chrome/Chromium major version, or None."""
    binary = config.chrome_binary
    if not binary:
        return None
    try:
        out = subprocess.check_output([binary, "--version"], text=True, timeout=15)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not read chrome version: %s", exc)
        return None
    match = re.search(r"(\d+)\.\d+\.\d+", out)
    return int(match.group(1)) if match else None


def display_available() -> bool:
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def _require_chrome(config: Config) -> None:
    if not config.chrome_binary:
        raise BrowserUnavailable(
            "No Chrome/Chromium binary found. Install chromium or set CHROME_BIN."
        )


def make_selenium_driver(config: Config, headless: bool = True):
    """Build a plain Selenium Chrome driver (used by Jobzella)."""
    _require_chrome(config)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError as exc:  # pragma: no cover
        raise BrowserUnavailable(f"selenium not installed: {exc}") from exc

    opts = Options()
    opts.binary_location = config.chrome_binary
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"--user-agent={config.user_agent}")
    if config.proxy:
        opts.add_argument(f"--proxy-server={config.proxy}")

    if config.chromedriver_binary:
        service = Service(executable_path=config.chromedriver_binary)
    else:  # fall back to webdriver-manager if a system driver isn't present
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
        except Exception as exc:  # noqa: BLE001
            raise BrowserUnavailable(
                f"No chromedriver found and webdriver-manager failed: {exc}"
            ) from exc
    return webdriver.Chrome(service=service, options=opts)


def make_uc_driver(config: Config, headless: bool | None = None):
    """Build an undetected-chromedriver Chrome driver (used by Bayt).

    Bayt is behind Cloudflare, which blocks headless browsers, so this
    defaults to headful when a display is available. undetected-chromedriver
    patches the driver binary in place, so we hand it a *writable copy* of
    the system chromedriver and pin ``version_main`` to the installed major.
    """
    _require_chrome(config)
    try:
        import undetected_chromedriver as uc
    except ImportError as exc:  # pragma: no cover
        raise BrowserUnavailable(f"undetected-chromedriver not installed: {exc}") from exc

    want_headless = (not config.headful) if headless is None else headless
    if not want_headless and not display_available():
        raise BrowserUnavailable(
            "Headful browser requested but no DISPLAY is available "
            "(set HEADFUL=0 to force headless, but Cloudflare may block it)."
        )

    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    if config.proxy:
        opts.add_argument(f"--proxy-server={config.proxy}")

    driver_path = _writable_driver_copy(config)
    major = detect_chrome_major(config)

    return uc.Chrome(
        options=opts,
        headless=want_headless,
        browser_executable_path=config.chrome_binary,
        driver_executable_path=driver_path,
        version_main=major,
    )


def _writable_driver_copy(config: Config) -> str | None:
    """Return a path to a writable chromedriver copy uc can patch, or None."""
    src = config.chromedriver_binary
    if not src:
        return None  # let uc download a matching driver itself
    if os.access(src, os.W_OK):
        return src
    dest = os.path.join(tempfile.gettempdir(), "uc_chromedriver")
    try:
        if not os.path.exists(dest) or os.path.getsize(dest) != os.path.getsize(src):
            shutil.copy2(src, dest)
        os.chmod(dest, 0o755)
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not create writable chromedriver copy: %s", exc)
        return src
