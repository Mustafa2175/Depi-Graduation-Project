# Producers — the ingestion layer

Each producer scrapes one job board and emits records in a single **uniform
contract** (`contract.py`), written to `data/raw/<source>/<date>/jobs_<run_id>.json`
(the Bronze layer). Because every producer outputs the same shape, the
downstream processing layer is completely source-agnostic.

## Layout

```
producers/
├── config.py       # env-driven settings (paths, rate limits, browser, query/volume caps)
├── contract.py     # the uniform record envelope + job_id hashing + salary formatting
├── http.py         # RateLimitedSession: retries (backoff, 429-aware) + rate limiting
├── browser.py      # lazy Chrome/undetected-chromedriver helpers + BrowserUnavailable
├── base.py         # BaseProducer: run() -> validate -> dedupe -> save JSON
├── registry.py     # name -> producer class (lazy import; no Selenium at import time)
├── runner.py       # CLI: run one/subset/all, skip browser sources gracefully
└── sources/        # one module per board
    ├── wuzzuf.py   # requests + detail-page description enrichment
    ├── forasna.py  # requests (Arabic IT listings)
    ├── jobzella.py # Selenium headless (__NEXT_DATA__)
    ├── bayt.py     # undetected-chromedriver headful (Cloudflare)
    └── indeed.py   # python-jobspy
```

## The contract

Every record has exactly these fields (strings are never `None` → `""`; `salary`
is **always** a string):

```
job_id, title, company, location, salary, description, experience,
posted_at_raw, industry, job_url, source, scraped_at, run_id
```

## Usage

```bash
make scrape                              # all available producers
make scrape SOURCES="wuzzuf forasna"     # subset
python -m producers.runner --list        # list known producers
PRODUCERS=wuzzuf,bayt python -m producers.runner

# Tunables (env or .env):
JOB_QUERY="data engineer"   # search scope ("" = broad)
MAX_JOBS=200 MAX_PAGES=5    # per-run volume caps
HEADFUL=0                   # force headless (Cloudflare may block Bayt)
SCRAPER_PROXY=http://...    # proxy for blocked IPs (e.g. Indeed on CI)
```

## Browser requirements

`jobzella`, `bayt`, and `indeed` need a real Chrome/Chromium + chromedriver
(install `requirements-browser.txt`). Bayt additionally needs a **display**
(headful) to clear Cloudflare. When any of these are missing, the runner logs a
skip and continues — the requests-based producers (`wuzzuf`, `forasna`) always run.
