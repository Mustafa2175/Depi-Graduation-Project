"""Wuzzuf producer — paginated search results via plain HTTP.

Wuzzuf serves fully-rendered HTML, so no browser is needed. Listing pages
carry title/company/location/url; salary and a richer description live on
the detail page, which we optionally fetch concurrently to improve skills
coverage downstream.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from producers.base import BaseProducer
from producers.config import Config
from producers.contract import build_record
from producers.http import RateLimitedSession

BASE_URL = "https://wuzzuf.net"


class WuzzufProducer(BaseProducer):
    source = "wuzzuf"
    home_url = BASE_URL

    def __init__(self, config: Config | None = None, enrich_details: bool = True):
        super().__init__(config)
        self.enrich_details = enrich_details
        self.session = RateLimitedSession(self.config)

    def _search_url(self, start: int) -> str:
        query = self.config.job_query.replace(" ", "%20")
        return f"{BASE_URL}/search/jobs?q={query}&start={start}"

    def fetch(self) -> list[dict]:
        jobs: list[dict] = []
        page = 0
        while len(jobs) < self.config.max_jobs:
            url = self._search_url(page)
            self.log.info("page %d", page)
            resp = self.session.get(url)
            if resp.status_code != 200:
                self.log.warning("stopped at page %d (HTTP %d)", page, resp.status_code)
                break
            page_jobs = self._parse_search(resp.content)
            if not page_jobs:
                self.log.info("no more jobs")
                break
            jobs.extend(page_jobs)
            page += 1

        jobs = jobs[: self.config.max_jobs]
        if self.enrich_details and jobs:
            self._enrich(jobs)
        self.session.close()
        return jobs

    def _parse_search(self, html: bytes) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        titles = soup.find_all("h2", {"class": "css-193uk2c"})
        companies = soup.find_all("a", {"class": "css-ipsyv7"})
        locations = soup.find_all("span", {"class": "css-16x61xq"})
        self.log.info("found %d jobs on page", len(titles))

        jobs: list[dict] = []
        for i, title_el in enumerate(titles):
            try:
                title = title_el.get_text(strip=True)
                company = companies[i].get_text(strip=True) if i < len(companies) else ""
                location = locations[i].get_text(strip=True) if i < len(locations) else ""
                anchor = title_el.find("a")
                job_url = BASE_URL + anchor["href"] if anchor and anchor.get("href") else ""
                jobs.append(
                    build_record(
                        source=self.source,
                        run_id=self.run_id,
                        title=title,
                        company=company,
                        location=location,
                        job_url=job_url,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                self.log.debug("skip card: %s", exc)
        return jobs

    # ── detail-page enrichment (salary + description) ────────
    def _enrich(self, jobs: list[dict]) -> None:
        self.log.info("enriching %d job detail pages (threads=%d)",
                      len(jobs), self.config.max_threads)
        with ThreadPoolExecutor(max_workers=self.config.max_threads) as pool:
            pool.map(self._enrich_one, jobs)

    #: detail-page section headers whose text feeds skills extraction
    _DESC_SECTIONS = ("Job Description", "Job Requirements", "Skills And Tools")

    def _enrich_one(self, job: dict) -> None:
        url = job.get("job_url")
        if not url:
            return
        try:
            resp = self.session.get(url)
            if resp.status_code != 200:
                return
            soup = BeautifulSoup(resp.content, "lxml")
            description = self._extract_sections(soup)
            if description:
                job["description"] = description[:2500]
        except Exception as exc:  # noqa: BLE001
            self.log.debug("enrich failed for %s: %s", url, exc)

    def _extract_sections(self, soup: BeautifulSoup) -> str:
        """Concatenate the Description/Requirements/Skills section bodies.

        Wuzzuf renders each section as a header followed by sibling nodes
        (interleaved with <style> tags) up to the next header, so we walk
        siblings rather than rely on a brittle content class.
        """
        parts: list[str] = []
        for header in soup.find_all(["h2", "h3", "h4"]):
            if header.get_text(strip=True) not in self._DESC_SECTIONS:
                continue
            for sib in header.find_next_siblings():
                if sib.name in ("h2", "h3", "h4"):
                    break
                if sib.name == "style":
                    continue
                text = sib.get_text(" ", strip=True)
                if text:
                    parts.append(text)
        return " ".join(parts)
