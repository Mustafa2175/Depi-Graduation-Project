"""The producer output contract.

Every producer — regardless of whether it scrapes with ``requests``,
Selenium, or a third-party library — emits records with *exactly* these
fields and types. This uniform "Bronze" envelope is what makes the
downstream processing layer fully source-agnostic.

Design rules:
* Every field is always present.
* String fields are never ``None`` — missing values are ``""``.
* ``salary`` is ALWAYS a string (e.g. ``"15000 - 20000 EGP"`` or ``""``);
  producers must format structured salary into a string here, so the
  processor never has to special-case a dict (the historical Indeed bug).
* ``job_id`` is a deterministic fingerprint of title+company+location.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

# Canonical field order (also the JSON key order).
CONTRACT_FIELDS = (
    "job_id",
    "title",
    "company",
    "location",
    "salary",
    "description",
    "experience",
    "posted_at_raw",
    "industry",
    "job_url",
    "source",
    "scraped_at",
    "run_id",
)

_STRING_DEFAULT_FIELDS = (
    "title",
    "company",
    "location",
    "salary",
    "description",
    "experience",
    "posted_at_raw",
    "industry",
    "job_url",
)


def generate_job_id(title: str, company: str, location: str) -> str:
    raw = f"{title}-{company}-{location}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _as_str(value: Any) -> str:
    """Coerce any value to a trimmed string; None/NaN -> ''."""
    if value is None:
        return ""
    # Guard against float NaN coming from pandas/jobspy.
    if isinstance(value, float) and value != value:  # NaN check
        return ""
    return str(value).strip()


def format_salary(
    min_amount: Any = None,
    max_amount: Any = None,
    currency: Any = None,
    interval: Any = None,
) -> str:
    """Build a human-readable salary string from structured parts.

    Returns ``""`` when no numeric bound is available so the processor's
    salary parser treats it as 'not specified'.
    """
    lo, hi = _as_str(min_amount), _as_str(max_amount)
    cur = _as_str(currency)
    iv = _as_str(interval)
    if not lo and not hi:
        return ""
    if lo and hi:
        body = f"{lo} - {hi}"
    else:
        body = lo or hi
    if cur:
        body = f"{body} {cur}"
    if iv:
        body = f"{body} / {iv}"
    return body


def build_record(
    *,
    source: str,
    run_id: str,
    title: Any,
    company: Any,
    location: Any,
    salary: Any = "",
    description: Any = "",
    experience: Any = "",
    posted_at_raw: Any = "",
    industry: Any = "",
    job_url: Any = "",
    scraped_at: str | None = None,
) -> dict:
    """Construct one contract-compliant record with defaults filled in."""
    title_s = _as_str(title) or "N/A"
    company_s = _as_str(company) or "N/A"
    location_s = _as_str(location) or "N/A"
    return {
        "job_id": generate_job_id(title_s, company_s, location_s),
        "title": title_s,
        "company": company_s,
        "location": location_s,
        "salary": _as_str(salary),
        "description": _as_str(description),
        "experience": _as_str(experience),
        "posted_at_raw": _as_str(posted_at_raw),
        "industry": _as_str(industry),
        "job_url": _as_str(job_url),
        "source": source,
        "scraped_at": scraped_at or datetime.now().isoformat(),
        "run_id": run_id,
    }


def validate_record(record: dict) -> list[str]:
    """Return a list of contract violations for a record (empty == valid)."""
    errors: list[str] = []
    for field_name in CONTRACT_FIELDS:
        if field_name not in record:
            errors.append(f"missing field: {field_name}")
    for field_name in _STRING_DEFAULT_FIELDS:
        if field_name in record and not isinstance(record[field_name], str):
            errors.append(f"field {field_name} must be str, got {type(record[field_name]).__name__}")
    if record.get("title") in (None, "", "N/A") and record.get("company") in (None, "", "N/A"):
        errors.append("record has neither title nor company")
    return errors
