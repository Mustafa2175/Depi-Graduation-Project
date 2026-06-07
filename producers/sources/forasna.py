"""Forasna producer — Arabic IT-jobs listings via plain HTTP.

Forasna serves server-rendered Arabic HTML and exposes salary directly on
the listing cards, so no detail-page fetch is needed.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from producers.base import BaseProducer
from producers.config import Config
from producers.contract import build_record
from producers.http import RateLimitedSession

BASE_URL = "https://forasna.com"
# Arabic: "IT & communications jobs in Egypt"
START_PATH = "/a/وظائف-تكنولوجيا-معلومات-واتصالات-في-مصر"


class ForasnaProducer(BaseProducer):
    source = "forasna"
    home_url = BASE_URL

    def __init__(self, config: Config | None = None):
        super().__init__(config)
        self.session = RateLimitedSession(self.config)
        self.session.raw.headers.update({"Referer": BASE_URL})

    def fetch(self) -> list[dict]:
        # warm up cookies
        try:
            self.session.get(BASE_URL)
        except Exception as exc:  # noqa: BLE001
            self.log.debug("warmup failed: %s", exc)

        jobs: list[dict] = []
        url: str | None = BASE_URL + START_PATH
        page = 1
        while url and page <= self.config.max_pages:
            self.log.info("page %d", page)
            resp = self.session.get(url)
            if resp.status_code != 200:
                self.log.warning("stopped at page %d (HTTP %d)", page, resp.status_code)
                break
            soup = BeautifulSoup(resp.text, "lxml")
            jobs.extend(self._parse(soup))
            url = self._next_page(soup)
            page += 1

        self.session.close()
        return jobs

    def _parse(self, soup: BeautifulSoup) -> list[dict]:
        cards = soup.select(".result-wrp")
        self.log.info("found %d jobs on page", len(cards))
        jobs: list[dict] = []
        for card in cards:
            try:
                title_tag = card.select_one("h2.job-title a span") or card.select_one(
                    "h2.job-title a"
                )
                title = title_tag.get_text(strip=True) if title_tag else ""

                company_tag = (
                    card.select_one("span.company-name a span")
                    or card.select_one("span.company-name a")
                    or card.select_one("span.company-name")
                )
                company = company_tag.get_text(strip=True) if company_tag else ""

                location_tag = card.select_one(
                    ".company-meta span.location-desktop span"
                ) or card.select_one(".location-mobile span.location span")
                location = location_tag.get_text(strip=True) if location_tag else ""

                salary = self._extract_salary(card)

                anchor = card.select_one("h2.job-title a")
                href = anchor.get("href") if anchor else ""
                if not href:
                    job_url = BASE_URL  # listing without a per-job link
                elif href.startswith("http"):
                    job_url = href
                else:
                    job_url = BASE_URL + href

                jobs.append(
                    build_record(
                        source=self.source,
                        run_id=self.run_id,
                        title=title,
                        company=company,
                        location=location,
                        salary=salary,
                        job_url=job_url,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.log.debug("skip card: %s", exc)
        return jobs

    @staticmethod
    def _extract_salary(card) -> str:
        for detail in card.select("div.job-details"):
            title_span = detail.select_one("span.job-details__title")
            if title_span and "الراتب" in title_span.get_text():
                for span in detail.select("span"):
                    if "job-details__title" not in span.get("class", []):
                        return span.get_text(strip=True)
        return ""

    @staticmethod
    def _next_page(soup: BeautifulSoup) -> str | None:
        nxt = soup.select_one("a[rel='next']")
        if nxt and nxt.get("href"):
            href = nxt["href"]
            return href if href.startswith("http") else BASE_URL + href
        return None
