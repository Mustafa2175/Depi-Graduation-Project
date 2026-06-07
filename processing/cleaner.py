"""The single, source-agnostic cleaner.

Because every producer emits the same uniform contract
(:mod:`producers.contract`), one cleaner handles all sources. It maps a raw
contract record into the canonical :class:`~processing.core.schema.JobSchema`
used by the Silver layer and the warehouse — applying the same normalization,
parsing, and enrichment rules to all records regardless of origin.

This replaces the previous per-source processor classes; the only
source-specific knowledge left is a homepage fallback for job URLs.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List

from processing.core.schema import JobSchema
from processing.utils import classifiers, cleaners, mappings, parsers
from processing.utils import skills as skills_util


def _job_hash(title: str, company: str, location: str) -> str:
    combined = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def clean_record(record: Dict) -> JobSchema:
    """Map one contract record to a canonical JobSchema row."""
    source = record.get("source", "")
    scraped_at = record.get("scraped_at") or ""

    title_raw = record.get("title", "") or ""
    title_clean = cleaners.strip_noise_from_title(title_raw)

    company_raw = (record.get("company") or "").strip() or "Confidential"
    company_clean = cleaners.clean_text(company_raw) or "Confidential"

    loc_raw = record.get("location", "") or ""
    city, gov = mappings.normalize_location(loc_raw)

    salary = parsers.parse_salary(record.get("salary", "") or "")
    exp_min, exp_max = parsers.parse_experience(record.get("experience", "") or "")

    description = record.get("description", "") or ""
    industry = record.get("industry", "") or ""
    experience_txt = record.get("experience", "") or ""

    skills_str = skills_util.extract_skills_str(
        title_raw, description, industry, experience_txt
    )
    work_mode = classifiers.classify_work_mode(title_raw, description, loc_raw)
    employment_type = classifiers.classify_employment_type(
        title_raw, description, experience_txt
    )

    # Producers own URL completeness (sources without per-job URLs fall back
    # to their homepage at scrape time); a still-empty URL here means a broken
    # record, which the validator will quarantine.
    job_url = record.get("job_url", "") or ""

    posted_at = parsers.parse_posted_date(
        record.get("posted_at_raw", "") or "", scraped_at
    ) if scraped_at else ""

    cleaned: JobSchema = {
        "job_id": record.get("job_id"),
        "job_hash": _job_hash(title_clean, company_clean, city),
        "title_raw": title_raw,
        "title_clean": title_clean,
        "company_raw": company_raw,
        "company_clean": company_clean,
        "location_raw": loc_raw,
        "location_city": city,
        "location_gov": gov,
        "salary_min": salary["min"],
        "salary_max": salary["max"],
        "salary_currency": salary["currency"],
        "salary_period": salary["period"],
        "experience_years_min": exp_min,
        "experience_years_max": exp_max,
        "skills": skills_str,
        "work_mode": work_mode,
        "employment_type": employment_type,
        "source": source,
        "job_url": job_url,
        "scraped_at": scraped_at,
        "posted_at": posted_at,
        "run_id": record.get("run_id"),
        "is_remote": work_mode == "remote",
    }
    return cleaned


def clean_file(path: str) -> List[JobSchema]:
    """Load a raw contract JSON file and clean every record (bad rows skipped)."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    out: List[JobSchema] = []
    for rec in raw:
        try:
            out.append(clean_record(rec))
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  skipping record from {path}: {exc}")
    return out
