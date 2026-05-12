"""
============================================================
  Job Market Tracker — Forasna Scraper (Production Version)
============================================================
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import hashlib
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────

BASE_URL = "https://forasna.com"
URL = BASE_URL + "/a/وظائف-تكنولوجيا-معلومات-واتصالات-في-مصر"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8",
    "Referer": BASE_URL,
}

SOURCE_NAME = "forasna"

# ── PATH SETUP (FIXED PATH) ───────────────────────────────────

CURRENT_FILE = os.path.abspath(__file__)
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

OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"jobs_{RUN_ID}.json")

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
    cards = soup.select(".result-wrp")

    log(f"Found {len(cards)} jobs on page")

    for card in cards:

        title_tag = card.select_one("h2.job-title a span") or card.select_one("h2.job-title a")
        title = title_tag.get_text(strip=True) if title_tag else "غير محدد"

        company_tag = (
            card.select_one("span.company-name a span")
            or card.select_one("span.company-name a")
            or card.select_one("span.company-name")
        )
        company = company_tag.get_text(strip=True) if company_tag else "غير محدد"

        location_tag = (
            card.select_one(".company-meta span.location-desktop span")
            or card.select_one(".location-mobile span.location span")
        )
        location = location_tag.get_text(strip=True) if location_tag else "غير محدد"

        salary = "غير محدد"
        for detail in card.select("div.job-details"):
            title_span = detail.select_one("span.job-details__title")
            if title_span and "الراتب" in title_span.get_text():
                spans = detail.select("span")
                for s in spans:
                    if "job-details__title" not in s.get("class", []):
                        salary = s.get_text(strip=True)
                        break

        job = {
            "job_id": generate_job_id(title, company, location),
            "title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "source": SOURCE_NAME,
            "scraped_at": datetime.now().isoformat(),
            "run_id": RUN_ID,
        }

        jobs.append(job)

    return jobs


def get_next_page(soup):
    next_btn = soup.select_one("a[rel='next']")
    if next_btn and next_btn.get("href"):
        href = next_btn["href"]
        return href if href.startswith("http") else BASE_URL + href
    return None


def scrape_forasna(max_pages=50):
    session = requests.Session()

    log("Initializing session...")
    session.get(BASE_URL, headers=HEADERS)
    time.sleep(1)

    all_jobs = []
    url = URL
    page = 1

    while url and page <= max_pages:
        log(f"Scraping page {page}")

        try:
            res = session.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            log(f"Request failed: {e}")
            break

        if res.status_code != 200:
            log(f"Bad status code: {res.status_code}")
            break

        soup = BeautifulSoup(res.text, "lxml")
        jobs = scrape_page(soup)
        all_jobs.extend(jobs)

        log(f"Collected {len(jobs)} jobs | Total: {len(all_jobs)}")

        url = get_next_page(soup)
        page += 1

        if url:
            time.sleep(1.5)

    log(f"Scraping finished. Total jobs: {len(all_jobs)}")
    return all_jobs


# ── STORAGE ───────────────────────────────────────────────────

def save_raw_json(jobs):
    ensure_dir(OUTPUT_DIR)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    log(f"Saved raw data → {OUTPUT_FILE}")


# ── RUN ───────────────────────────────────────────────────────

if __name__ == "__main__":
    log("Starting Forasna scraper...")

    jobs = scrape_forasna(max_pages=50)

    if jobs:
        save_raw_json(jobs)
        log("Done successfully ✅")
    else:
        log("No jobs found ⚠️")