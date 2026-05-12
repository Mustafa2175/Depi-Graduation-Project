"""
============================================================
  Job Market Tracker — Indeed Scraper (Production Version)
============================================================
"""

import json
import logging
import math
import os
import hashlib

from datetime import datetime
from pathlib import Path
from typing import Optional, List

from jobspy import scrape_jobs


# ── CONFIG ────────────────────────────────────────────────────

SOURCE_NAME = "indeed"

DEFAULT_TERMS = [
    "software engineer",
    "data engineer",
    "data scientist",
    "backend developer",
    "frontend developer",
    "devops engineer",
    "machine learning engineer",
]

SEARCH_TERMS: List[str] = DEFAULT_TERMS

LOCATION = "Egypt"

COUNTRY = "Egypt"

RESULTS_PER_TERM = 50


# ── PATH SETUP (FIXED PATH) ───────────────────────────────────

CURRENT_FILE = os.path.abspath(__file__)

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(CURRENT_FILE)
)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

RUN_DATE = datetime.now().strftime("%Y-%m-%d")

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "raw",
    SOURCE_NAME,
    RUN_DATE
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    f"jobs_{RUN_ID}.json"
)


# ── LOGGING ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ── HELPERS ───────────────────────────────────────────────────

def ensure_dir(path):

    os.makedirs(path, exist_ok=True)


def log(msg):

    logger.info(msg)


def generate_job_id(title, company, location):

    raw = f"{title}-{company}-{location}"

    return hashlib.md5(raw.encode()).hexdigest()


def safe_str(val) -> Optional[str]:

    if val is None:

        return None

    try:

        if math.isnan(float(val)):

            return None

    except (TypeError, ValueError):

        pass

    s = str(val).strip()

    return s if s else None


def safe_float(val) -> Optional[float]:

    if val is None:

        return None

    try:

        f = float(val)

        return None if math.isnan(f) else f

    except (TypeError, ValueError):

        return None


# ── SALARY PARSER ─────────────────────────────────────────────

def parse_salary(row):

    min_sal = safe_float(
        row.get("min_amount")
    )

    max_sal = safe_float(
        row.get("max_amount")
    )

    currency = safe_str(
        row.get("currency")
    )

    interval = safe_str(
        row.get("interval")
    )

    if min_sal is None and max_sal is None:

        return "N/A"

    return {
        "min": min_sal,
        "max": max_sal,
        "currency": currency,
        "interval": interval,
    }


# ── CLEAN ROW ─────────────────────────────────────────────────

def clean_row(row):

    desc = safe_str(
        row.get("description")
    )

    title = safe_str(
        row.get("title")
    ) or "N/A"

    company = safe_str(
        row.get("company")
    ) or "N/A"

    location = safe_str(
        row.get("location")
    ) or "N/A"

    return {

        "job_id": generate_job_id(
            title,
            company,
            location
        ),

        "title": title,

        "company": company,

        "location": location,

        "salary": parse_salary(row),

        "job_url": safe_str(
            row.get("job_url")
        ),

        "description": (
            desc[:500]
            if desc
            else "N/A"
        ),

        "date_posted": safe_str(
            row.get("date_posted")
        ),

        "source": SOURCE_NAME,

        "scraped_at": datetime.now().isoformat(),

        "run_id": RUN_ID,
    }


# ── MAIN SCRAPER ──────────────────────────────────────────────

def scrape_indeed_jobs():

    all_jobs = []

    seen_urls = set()

    for term in SEARCH_TERMS:

        log(f"Scraping '{term}' jobs...")

        try:

            df = scrape_jobs(

                site_name=["indeed"],

                search_term=term,

                location=LOCATION,

                results_wanted=RESULTS_PER_TERM,

                hours_old=72,

                country_indeed=COUNTRY,
            )

            if df is None or df.empty:

                log(f"No jobs found for '{term}'")

                continue

            new_jobs = 0

            for _, row in df.iterrows():

                job = clean_row(row)

                url = job.get("job_url") or ""

                # ── DEDUPLICATION ─────────────────

                if url and url in seen_urls:

                    continue

                seen_urls.add(url)

                all_jobs.append(job)

                new_jobs += 1

            log(
                f"Collected {new_jobs} jobs "
                f"for '{term}'"
            )

        except Exception as e:

            log(
                f"Failed scraping '{term}': {e}"
            )

    log(
        f"Scraping finished. "
        f"Total jobs: {len(all_jobs)}"
    )

    return all_jobs


# ── STORAGE ───────────────────────────────────────────────────

def save_raw_json(jobs):

    ensure_dir(OUTPUT_DIR)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jobs,
            f,
            ensure_ascii=False,
            indent=2
        )

    log(f"Saved raw data → {OUTPUT_FILE}")


# ── RUN ───────────────────────────────────────────────────────

if __name__ == "__main__":

    log("Starting Indeed scraper...")

    start_time = datetime.now()

    jobs = scrape_indeed_jobs()

    if jobs:

        save_raw_json(jobs)

        duration = datetime.now() - start_time

        log(
            f"Done successfully ✅ | "
            f"Total jobs: {len(jobs)} | "
            f"Duration: {duration}"
        )

    else:

        log("No jobs found ⚠️")