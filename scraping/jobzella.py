"""
============================================================
  Job Market Tracker — Jobzella Scraper (Production Version)
============================================================
"""

import json
import time
import os
import hashlib

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup


# ── CONFIG ────────────────────────────────────────────────────

BASE_URL = "https://www.jobzella.com"

SEARCH_URL = "https://www.jobzella.com/search/jobs?page={}"

SOURCE_NAME = "jobzella"

MAX_PAGES = 107


# ── TECH FILTER ───────────────────────────────────────────────

TECH_KEYWORDS = [
    "software",
    "information technology",
    "tech",
    "developer",
    "data",
    "it",
    "backend",
    "frontend",
    "fullstack",
    "machine learning",
    "cyber",
    "devops",
    "ux/ui",
    "embedded systems",
    "ar",
    "vr",
    "mobile developer",
    "game developer",
    "database administrator",
    "dba",
    "ai",
    "cybersecurity",
    "hacker",
    "social media manager"
]


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


# ── DRIVER SETUP ──────────────────────────────────────────────

def setup_driver():

    chrome_options = Options()

    chrome_options.add_argument("--headless")

    chrome_options.add_argument("--disable-gpu")

    chrome_options.add_argument("--log-level=3")

    service = Service(
        ChromeDriverManager().install()
    )

    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )

    return driver


# ── PAGE SCRAPER ──────────────────────────────────────────────

def scrape_page(driver, page_num):

    jobs = []

    url = SEARCH_URL.format(page_num)

    log(f"Scraping page {page_num}")

    driver.get(url)

    html = driver.page_source

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    next_data_script = soup.find(
        "script",
        id="__NEXT_DATA__"
    )

    if not next_data_script:

        log(f"No data found on page {page_num}")

        return jobs

    try:

        data = json.loads(
            next_data_script.string
        )

        page_jobs = (
            data["props"]
            ["pageProps"]
            ["jobs"]
        )

    except Exception as e:

        log(f"Data extraction failed: {e}")

        return jobs

    for job in page_jobs:

        try:

            # ── EXTRACT DATA ───────────────────────────

            title = (
                job.get("position", {})
                .get("name")
                or "N/A"
            )

            company = (
                job.get("company", {})
                .get("title")
                or "N/A"
            )

            location = (
                job.get("location")
                or "N/A"
            )

            industry = (
                job.get("jobRole", {})
                .get("name")
                or "N/A"
            )

            min_sal = job.get("min_salary")

            max_sal = job.get("max_salary")

            currency = (
                job.get("currency")
                or ""
            )

            # ── SALARY ─────────────────────────────────

            if min_sal and max_sal:

                salary = (
                    f"{min_sal} - "
                    f"{max_sal} "
                    f"{currency}"
                )

            else:

                salary = "N/A"

            # ── TECH FILTER ───────────────────────────

            title_lower = title.lower()

            industry_lower = industry.lower()

            is_tech_job = any(
                keyword in title_lower
                or keyword in industry_lower
                for keyword in TECH_KEYWORDS
            )

            if not is_tech_job:

                continue

            # ── JOB OBJECT ────────────────────────────

            extracted_job = {
                "job_id": generate_job_id(
                    title,
                    company,
                    location
                ),
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "industry": industry,
                "source": SOURCE_NAME,
                "scraped_at": datetime.now().isoformat(),
                "run_id": RUN_ID,
            }

            jobs.append(extracted_job)

        except Exception as e:

            log(f"Error extracting job: {e}")

    return jobs


# ── MAIN SCRAPER ──────────────────────────────────────────────

def scrape_jobzella_jobs():

    all_jobs = []

    log("Initializing browser...")

    driver = setup_driver()

    try:

        for page_num in range(1, MAX_PAGES + 1):

            page_jobs = scrape_page(
                driver,
                page_num
            )

            if not page_jobs:

                continue

            all_jobs.extend(page_jobs)

            log(
                f"Collected {len(page_jobs)} jobs | "
                f"Total: {len(all_jobs)}"
            )

    finally:

        driver.quit()

    # ── REMOVE DUPLICATES ─────────────────────────────

    unique_jobs = [
        dict(job)
        for job in {
            tuple(d.items())
            for d in all_jobs
        }
    ]

    log(
        f"After deduplication: "
        f"{len(unique_jobs)} jobs"
    )

    return unique_jobs


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

    start_time = time.time()

    log("Starting Jobzella scraper...")

    jobs = scrape_jobzella_jobs()

    if jobs:

        save_raw_json(jobs)

        execution_time = round(
            time.time() - start_time,
            2
        )

        log(
            f"Done successfully ✅ | "
            f"Total jobs: {len(jobs)} | "
            f"Time: {execution_time} sec"
        )

    else:

        log("No jobs found ⚠️")