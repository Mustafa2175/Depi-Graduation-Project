from typing import TypedDict, Optional

class JobSchema(TypedDict):
    # Required Fields (Must be present in every processed record)
    job_id: str             # Original ID from source
    job_hash: str           # Deduplication Fingerprint (title+company+location)
    title_raw: str
    title_clean: str
    company_raw: str
    company_clean: str
    location_raw: str
    location_city: str
    location_gov: str
    
    # Optional/Nullable Fields
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_currency: Optional[str]
    experience_years_min: Optional[int]
    experience_years_max: Optional[int]
    
    # Metadata
    source: str             # wuzzuf, bayt, etc.
    job_url: str
    scraped_at: str         # ISO format
    posted_at: str          # Normalized date string (YYYY-MM-DD)
    run_id: str
    is_remote: bool
