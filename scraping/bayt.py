"""
============================================================
  Job Market Tracker — Bayt Scraper (Production Version)
============================================================
"""

import json
import time
import os
import hashlib
from datetime import datetime

from bs4 import BeautifulSoup

import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ── CONFIG ────────────────────────────────────────────────────

BASE_URL = "https://www.bayt.com"
START_URL = "https://www.bayt.com/en/egypt/jobs/"

SOURCE_NAME = "bayt"

MAX_PAGES = 10


# ── PATH SETUP (FIXED PATH) ───────────────────────────────────

CURRENT_FILE = os.path.abspath(__file__)

# project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_FILE))

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── SCRAPER ───────────────────────────────────────────────────

def scrape_page(soup):

    jobs = []

    job_cards = soup.select("li.has-pointer-d")

    log(f"Found {len(job_cards)} jobs on page")

    for card in job_cards:

        try:

            # ── TITLE ───────────────────────────────────────

            title_elem = card.select_one("h2 a")

            title = (
                title_elem.get_text(strip=True)
                if title_elem
                else "N/A"
            )

            # ── JOB URL ────────────────────────────────────

            job_url = ""

            if title_elem and title_elem.get("href"):

                href = title_elem.get("href")

                job_url = (
                    href
                    if href.startswith("http")
                    else BASE_URL + href
                )

            # ── COMPANY ────────────────────────────────────

            company_elem = (
                card.select_one(
                    "div.job-company-location-wrapper > a"
                )
                or
                card.select_one(
                    "div.job-company-location-wrapper > b"
                )
            )

            company = (
                company_elem.get_text(strip=True)
                if company_elem
                else "N/A"
            )

            # ── LOCATION ───────────────────────────────────

            location_elems = card.select(
                "div.t-mute.t-small a.t-mute"
            )

            location = ", ".join([
                loc.get_text(strip=True)
                for loc in location_elems
            ]) if location_elems else "N/A"

            # ── DESCRIPTION ────────────────────────────────

            desc_elem = card.select_one("div.jb-descr")

            description = (
                desc_elem.get_text(strip=True)
                .replace("Summary: \n", "")
                .strip()
                if desc_elem
                else "N/A"
            )

            # ── SALARY ─────────────────────────────────────

            salary_elem = card.select_one("dt.jb-label-salary")

            salary = (
                salary_elem.get_text(strip=True)
                if salary_elem
                else "N/A"
            )

            # ── EXPERIENCE ─────────────────────────────────

            exp_elem = card.select_one("dt.jb-label-careerlevel")

            experience = (
                exp_elem.get_text(strip=True)
                .replace(" · ", " - ")
                if exp_elem
                else "N/A"
            )

            # ── POST DATE ──────────────────────────────────

            date_elem = card.select_one("div.jb-date span")

            post_date = (
                date_elem.get_text(strip=True)
                if date_elem
                else "N/A"
            )

            # ── JOB OBJECT ─────────────────────────────────

            job = {
                "job_id": generate_job_id(
                    title,
                    company,
                    location
                ),
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "experience": experience,
                "post_date": post_date,
                "description": description,
                "job_url": job_url,
                "source": SOURCE_NAME,
                "scraped_at": datetime.now().isoformat(),
                "run_id": RUN_ID,
            }

            jobs.append(job)

        except Exception as e:

            log(f"Error extracting job: {e}")

    return jobs


def scrape_bayt_jobs(max_pages=MAX_PAGES):

    jobs_data = []

    # ── CHROME OPTIONS ───────────────────────────────────

    options = uc.ChromeOptions()

    # options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")

    log("Starting browser...")

    driver = uc.Chrome(
        options=options,
        version_main=147
    )

    page_num = 1

    try:

        while page_num <= max_pages:

            url = (
                f"{START_URL}?page={page_num}"
                if page_num > 1
                else START_URL
            )

            log(f"Navigating to page {page_num}")

            driver.get(url)

            # ── WAIT FOR PAGE LOAD ───────────────────────

            try:

                log("Waiting for jobs to load...")

                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "li.has-pointer-d"
                        )
                    )
                )

            except Exception:

                log("Jobs not found after waiting.")

            # ── PAGE SOURCE ──────────────────────────────

            html = driver.page_source

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            jobs = scrape_page(soup)

            if not jobs:

                log("No more jobs found.")

                break

            jobs_data.extend(jobs)

            log(
                f"Collected {len(jobs)} jobs | "
                f"Total: {len(jobs_data)}"
            )

            page_num += 1

            time.sleep(3)

    except KeyboardInterrupt:

        log("Scraping interrupted by user.")

    finally:

        driver.quit()

    log(
        f"Scraping finished. "
        f"Total jobs: {len(jobs_data)}"
    )

    return jobs_data


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

    log("Starting Bayt scraper...")

    jobs = scrape_bayt_jobs()

    if jobs:

        save_raw_json(jobs)

        log("Done successfully ✅")

    else:

        log("No jobs found ⚠️")