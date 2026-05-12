from processing.core.base import BaseProcessor
from processing.utils import mappings, cleaners, parsers
from processing.core.schema import JobSchema
from typing import Dict

class ForasnaProcessor(BaseProcessor):
    def __init__(self):
        super().__init__(source_name="forasna")

    def process_record(self, record: Dict) -> JobSchema:
        title_raw = record.get('title', '')
        title_clean = cleaners.clean_text(title_raw)
        company_clean = cleaners.clean_text(record.get('company', ''))
        city, gov = mappings.normalize_location(record.get('location', ''))
        
        # FIX: Ensure job_url is never empty
        job_url = record.get('job_url')
        if not job_url or job_url == "":
            job_url = "https://forasna.com"
            
        return {
            "job_id": record.get('job_id'),
            "job_hash": self.generate_job_hash(title_clean, company_clean, city),
            "title_raw": title_raw, "title_clean": title_clean,
            "company_raw": record.get('company', ''), "company_clean": company_clean,
            "location_raw": record.get('location', ''), "location_city": city, "location_gov": gov,
            "salary_min": None, "salary_max": None, "salary_currency": "EGP",
            "experience_years_min": None, "experience_years_max": None,
            "source": self.source_name, "job_url": job_url,
            "scraped_at": record.get('scraped_at'), "posted_at": record.get('scraped_at')[:10],
            "run_id": record.get('run_id'), "is_remote": False
        }

class JobzellaProcessor(BaseProcessor):
    def __init__(self):
        super().__init__(source_name="jobzella")

    def process_record(self, record: Dict) -> JobSchema:
        title_raw = record.get('title', '')
        title_clean = cleaners.strip_noise_from_title(title_raw)
        company_clean = cleaners.clean_text(record.get('company', ''))
        city, gov = mappings.normalize_location(record.get('location', ''))
        salary_info = parsers.parse_salary(record.get('salary', ''))
        
        # FIX: Ensure job_url is never empty
        job_url = record.get('job_url')
        if not job_url or job_url == "":
            job_url = "https://www.jobzella.com"
            
        return {
            "job_id": record.get('job_id'),
            "job_hash": self.generate_job_hash(title_clean, company_clean, city),
            "title_raw": title_raw, "title_clean": title_clean,
            "company_raw": record.get('company', ''), "company_clean": company_clean,
            "location_raw": record.get('location', ''), "location_city": city, "location_gov": gov,
            "salary_min": salary_info['min'], "salary_max": salary_info['max'], "salary_currency": salary_info['currency'],
            "experience_years_min": None, "experience_years_max": None,
            "source": self.source_name, "job_url": job_url,
            "scraped_at": record.get('scraped_at'), "posted_at": record.get('scraped_at')[:10],
            "run_id": record.get('run_id'), "is_remote": "remote" in title_raw.lower()
        }
