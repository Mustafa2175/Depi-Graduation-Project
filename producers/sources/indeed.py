"""Indeed producer — backed by the jobspy library.

jobspy returns a pandas DataFrame; we map each row into the uniform
contract, formatting jobspy's structured salary columns into a single
salary string so downstream code never sees a dict (the historical bug).
"""
from __future__ import annotations

from producers.base import BaseProducer
from producers.browser import BrowserUnavailable
from producers.contract import build_record, format_salary

DEFAULT_TERMS = (
    "software engineer",
    "data engineer",
    "data scientist",
    "backend developer",
    "frontend developer",
    "devops engineer",
    "machine learning engineer",
)


class IndeedProducer(BaseProducer):
    source = "indeed"
    home_url = "https://eg.indeed.com"

    def fetch(self) -> list[dict]:
        try:
            from jobspy import scrape_jobs
        except ImportError as exc:
            raise BrowserUnavailable(f"python-jobspy not installed: {exc}") from exc

        terms = [self.config.job_query] if self.config.job_query else list(DEFAULT_TERMS)
        per_term = max(10, self.config.max_jobs // max(1, len(terms)))

        jobs: list[dict] = []
        for term in terms:
            self.log.info("scraping '%s'", term)
            try:
                df = scrape_jobs(
                    site_name=["indeed"],
                    search_term=term,
                    location="Egypt",
                    results_wanted=per_term,
                    hours_old=168,
                    country_indeed="Egypt",
                    proxies=[self.config.proxy] if self.config.proxy else None,
                )
            except Exception as exc:  # noqa: BLE001
                self.log.warning("term '%s' failed: %s", term, exc)
                continue
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                jobs.append(self._row_to_record(row))
            if len(jobs) >= self.config.max_jobs:
                break
        return jobs[: self.config.max_jobs]

    def _row_to_record(self, row) -> dict:
        salary = format_salary(
            row.get("min_amount"),
            row.get("max_amount"),
            row.get("currency"),
            row.get("interval"),
        )
        return build_record(
            source=self.source,
            run_id=self.run_id,
            title=row.get("title"),
            company=row.get("company"),
            location=row.get("location"),
            salary=salary,
            description=row.get("description"),
            posted_at_raw=row.get("date_posted"),
            job_url=row.get("job_url"),
        )
