"""
============================================================
  Job Market Tracker — Wuzzuf Scraper (Production Version)
============================================================
"""

import requests
from bs4 import BeautifulSoup

import json
import os
import time
import hashlib

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


# ── CONFIG ────────────────────────────────────────────────────

BASE_URL = "https://wuzzuf.net"

SEARCH_URL = "https://wuzzuf.net/search/jobs?q=&start={}"

SOURCE_NAME = "wuzzuf"

MAX_JOBS = 5300

MAX_THREADS = 15


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


# ── SESSION SETUP ─────────────────────────────────────────────

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
})


# ── HELPERS ───────────────────────────────────────────────────

def ensure_dir(path):

    os.makedirs(path, exist_ok=True)


def generate_job_id(title, company, location):

    raw = f"{title}-{company}-{location}"

    return hashlib.md5(raw.encode()).hexdigest()


def log(msg):

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    )


# ── SALARY SCRAPER ────────────────────────────────────────────

def get_salary_worker(job):

    try:

        res = session.get(
            job["job_url"],
            timeout=10
        )

        soup = BeautifulSoup(
            res.content,
            "lxml"
        )

        salary_elem = soup.find(
            "span",
            {"class": "css-iu2m7n"}
        )

        if salary_elem:

            job["salary"] = (
                salary_elem.get_text(strip=True)
            )

        else:

            job["salary"] = "N/A"

    except Exception:

        job["salary"] = "N/A"

    return job


# ── PAGE SCRAPER ──────────────────────────────────────────────

def scrape_search_page(soup):

    jobs = []

    titles = soup.find_all(
        "h2",
        {"class": "css-193uk2c"}
    )

    companies = soup.find_all(
        "a",
        {"class": "css-ipsyv7"}
    )

    locations = soup.find_all(
        "span",
        {"class": "css-16x61xq"}
    )

    log(f"Found {len(titles)} jobs on page")

    for i in range(len(titles)):

        try:

            title = titles[i].get_text(strip=True)

            company = (
                companies[i].get_text(strip=True)
                if i < len(companies)
                else "N/A"
            )

            location = (
                locations[i].get_text(strip=True)
                if i < len(locations)
                else "N/A"
            )

            relative_url = (
                titles[i]
                .find("a")
                .attrs["href"]
            )

            job_url = (
                BASE_URL + relative_url
            )

            job = {
                "job_id": generate_job_id(
                    title,
                    company,
                    location
                ),
                "title": title,
                "company": company,
                "location": location,
                "salary": "N/A",
                "job_url": job_url,
                "source": SOURCE_NAME,
                "scraped_at": datetime.now().isoformat(),
                "run_id": RUN_ID,
            }

            jobs.append(job)

        except Exception as e:

            log(f"Error extracting job: {e}")

    return jobs


# ── MAIN SCRAPER ──────────────────────────────────────────────

def scrape_wuzzuf_jobs():

    all_jobs = []

    page_num = 0

    log("Starting Wuzzuf scraping...")

    while True:

        try:

            url = SEARCH_URL.format(page_num)

            log(f"Scraping page {page_num}")

            response = session.get(
                url,
                timeout=15
            )

            if response.status_code != 200:

                log(
                    f"Connection stopped "
                    f"at page {page_num}"
                )

                break

            soup = BeautifulSoup(
                response.content,
                "lxml"
            )

            page_jobs = scrape_search_page(soup)

            if not page_jobs:

                log("No more jobs found.")

                break

            all_jobs.extend(page_jobs)

            log(
                f"Collected {len(page_jobs)} jobs | "
                f"Total: {len(all_jobs)}"
            )

            if len(all_jobs) >= MAX_JOBS:

                log(
                    f"Reached target "
                    f"({MAX_JOBS} jobs)"
                )

                break

            page_num += 1

            time.sleep(0.5)

        except Exception as e:

            log(f"Scraping stopped: {e}")

            break

    return all_jobs


# ── ENRICHMENT ────────────────────────────────────────────────

def enrich_jobs_with_salary(jobs):

    log(
        f"Fetching salaries using "
        f"{MAX_THREADS} threads..."
    )

    with ThreadPoolExecutor(
        max_workers=MAX_THREADS
    ) as executor:

        jobs = list(
            executor.map(
                get_salary_worker,
                jobs
            )
        )

    return jobs


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

    jobs = scrape_wuzzuf_jobs()

    if jobs:

        jobs = enrich_jobs_with_salary(jobs)

        save_raw_json(jobs)

        log(
            f"Done successfully ✅ | "
            f"Total jobs: {len(jobs)}"
        )

    else:

        log("No jobs found ⚠️")