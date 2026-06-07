#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Local (non-Docker) dependency setup. Installs the app dependencies and
# creates a dedicated Python 3.12 virtualenv for dbt (dbt does not support
# Python 3.13+/3.14). Requires `uv` (https://docs.astral.sh/uv/) which can
# fetch the right Python automatically.
#
# After this, run:  ./scripts/bootstrap.sh
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: 'uv' is required for local setup (it provisions Python 3.12)."
  echo "Install it: https://docs.astral.sh/uv/getting-started/installation/"
  echo "Or just use Docker:  docker compose up --build"
  exit 1
fi

# A single Python 3.12 virtualenv (.venv) holds the app, dbt, and (optionally)
# the browser-based producers. This avoids the classic "works on my machine"
# trap where the developer's system Python (e.g. 3.13/3.14) has no matching
# wheels for the pinned dependencies — uv fetches a known-good 3.12 regardless
# of what's installed.
echo "==> Creating Python 3.12 virtualenv (.venv) ..."
uv venv --python 3.12 .venv

echo "==> Installing app + dbt dependencies into it ..."
uv pip install --python .venv/bin/python -r requirements.txt -r dbt-requirements.txt

# Browser-based producers (Bayt, Jobzella, Indeed) are optional and heavy; skip
# with SKIP_BROWSER=1. They also need a real Chrome/Chromium + chromedriver.
if [ "${SKIP_BROWSER:-0}" != "1" ]; then
  echo "==> Installing optional browser-producer dependencies ..."
  uv pip install --python .venv/bin/python -r requirements-browser.txt
fi

echo "==> Local setup complete."
echo "    Next:  cp .env.example .env   (then edit if needed)"
echo "           ./scripts/bootstrap.sh"
