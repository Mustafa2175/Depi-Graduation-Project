"""Bayt producer — scraped via undetected-chromedriver (headful).

Bayt sits behind Cloudflare's bot challenge, which blocks headless
browsers; undetected-chromedriver running *headful* on a display clears it.
Listing cards carry a rich set of fields including a description and
experience, which improve downstream skills/seniority signals.
"""
from __future__ import annotations

import time

from bs4 import BeautifulSoup

from producers.base import BaseProducer
from producers.browser import make_uc_driver
from producers.contract import build_record

BASE_URL = "https://www.bayt.com"
START_URL = "https://www.bayt.com/en/egypt/jobs/"


class BaytProducer(BaseProducer):
    source = "bayt"
    home_url = BASE_URL

    def fetch(self) -> list[dict]:
        driver = make_uc_driver(self.config)  # headful by default
        jobs: list[dict] = []
        try:
            for page in range(1, self.config.max_pages + 1):
                url = START_URL if page == 1 else f"{START_URL}?page={page}"
                self.log.info("page %d", page)
                driver.get(url)
                page_jobs = self._wait_and_parse(driver)
                if not page_jobs:
                    self.log.info("no jobs on page %d, stopping", page)
                    break
                jobs.extend(page_jobs)
                if len(jobs) >= self.config.max_jobs:
                    break
                time.sleep(2)
        finally:
            driver.quit()
        return jobs[: self.config.max_jobs]

    def _wait_and_parse(self, driver) -> list[dict]:
        # poll until Cloudflare clears and cards render (or we give up)
        deadline = self.config.browser_wait_seconds + 12
        waited = 0
        cards = []
        while waited < deadline:
            time.sleep(3)
            waited += 3
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("li.has-pointer-d")
            if cards:
                break
        self.log.info("found %d cards (waited %ds)", len(cards), waited)
        return [self._parse_card(c) for c in cards if self._parse_card(c)]

    def _parse_card(self, card) -> dict | None:
        try:
            title_el = card.select_one("h2 a")
            title = title_el.get_text(strip=True) if title_el else ""
            href = title_el.get("href") if title_el else ""
            job_url = href if href.startswith("http") else (BASE_URL + href if href else "")

            company_el = card.select_one(
                "div.job-company-location-wrapper > a"
            ) or card.select_one("div.job-company-location-wrapper > b")
            company = company_el.get_text(strip=True) if company_el else ""

            loc_els = card.select("div.t-mute.t-small a.t-mute")
            location = ", ".join(le.get_text(strip=True) for le in loc_els) if loc_els else ""

            desc_el = card.select_one("div.jb-descr")
            description = (
                desc_el.get_text(" ", strip=True).replace("Summary:", "").strip()
                if desc_el
                else ""
            )

            salary_el = card.select_one("dt.jb-label-salary")
            salary = salary_el.get_text(strip=True) if salary_el else ""

            exp_el = card.select_one("dt.jb-label-careerlevel")
            experience = exp_el.get_text(strip=True).replace(" · ", " - ") if exp_el else ""

            date_el = card.select_one("div.jb-date span")
            posted = date_el.get_text(strip=True) if date_el else ""

            return build_record(
                source=self.source,
                run_id=self.run_id,
                title=title,
                company=company,
                location=location,
                salary=salary,
                description=description,
                experience=experience,
                posted_at_raw=posted,
                job_url=job_url,
            )
        except Exception as exc:  # noqa: BLE001
            self.log.debug("skip card: %s", exc)
            return None
