"""Jobzella producer — Next.js site scraped via headless Selenium.

Job data is embedded in the page's ``__NEXT_DATA__`` JSON, which only
appears after the page's JavaScript runs, so a real browser is required.
A tech-keyword filter keeps the dataset focused on IT roles.
"""
from __future__ import annotations

import json
import time

from bs4 import BeautifulSoup

from producers.base import BaseProducer
from producers.browser import make_selenium_driver

SEARCH_URL = "https://www.jobzella.com/search/jobs?page={}"
BASE_URL = "https://www.jobzella.com"

TECH_KEYWORDS = (
    "software", "information technology", "tech", "developer", "data", "it",
    "backend", "frontend", "fullstack", "machine learning", "cyber", "devops",
    "ux/ui", "embedded", "mobile developer", "game developer", "database",
    "dba", "ai", "cybersecurity", "qa", "network", "system admin",
)


class JobzellaProducer(BaseProducer):
    source = "jobzella"
    home_url = BASE_URL

    def fetch(self) -> list[dict]:
        from producers.contract import build_record, format_salary

        driver = make_selenium_driver(self.config, headless=not self.config.headful)
        jobs: list[dict] = []
        try:
            for page in range(1, self.config.max_pages + 1):
                self.log.info("page %d", page)
                driver.get(SEARCH_URL.format(page))
                time.sleep(self.config.browser_wait_seconds)
                page_jobs = self._parse(driver.page_source, build_record, format_salary)
                if not page_jobs:
                    self.log.info("no jobs on page %d, stopping", page)
                    break
                jobs.extend(page_jobs)
                if len(jobs) >= self.config.max_jobs:
                    break
        finally:
            driver.quit()
        return jobs[: self.config.max_jobs]

    def _parse(self, html: str, build_record, format_salary) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            return []
        try:
            data = json.loads(script.string)
            page_jobs = data["props"]["pageProps"]["jobs"]
        except (KeyError, json.JSONDecodeError) as exc:
            self.log.debug("could not read __NEXT_DATA__: %s", exc)
            return []

        jobs: list[dict] = []
        for job in page_jobs:
            title = (job.get("position") or {}).get("name") or ""
            industry = (job.get("jobRole") or {}).get("name") or ""
            if not self._is_tech(title, industry):
                continue
            company = (job.get("company") or {}).get("title") or ""
            location = job.get("location") or ""
            salary = format_salary(
                job.get("min_salary"), job.get("max_salary"), job.get("currency")
            )
            jobs.append(
                build_record(
                    source=self.source,
                    run_id=self.run_id,
                    title=title,
                    company=company,
                    location=location,
                    salary=salary,
                    industry=industry,
                    job_url=BASE_URL,
                )
            )
        return jobs

    @staticmethod
    def _is_tech(title: str, industry: str) -> bool:
        blob = f"{title} {industry}".lower()
        return any(kw in blob for kw in TECH_KEYWORDS)
