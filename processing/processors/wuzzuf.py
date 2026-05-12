from processing.core.base import BaseProcessor
from processing.utils import mappings, cleaners, parsers
from processing.core.schema import JobSchema
from typing import Dict

class WuzzufProcessor(BaseProcessor):
    def __init__(self):
        super().__init__(source_name="wuzzuf")

    def process_record(self, record: Dict) -> JobSchema:
        title_raw = record.get('title', '')
        title_clean = cleaners.strip_noise_from_title(title_raw)
        company_raw = record.get('company', '').replace(' -', '').strip()
        company_clean = cleaners.clean_text(company_raw)
        
        # Wuzzuf location often looks like "Maadi, Cairo, Egypt"
        loc_raw = record.get('location', '')
        city, gov = mappings.normalize_location(loc_raw)
        
        salary_info = parsers.parse_salary(record.get('salary', ''))
        
        # Wuzzuf raw data doesn't always have exp years in the main list, 
        # but we'll prepare the schema anyway
        processed: JobSchema = {
            "job_id": record.get('job_id'),
            "job_hash": self.generate_job_hash(title_clean, company_clean, city),
            "title_raw": title_raw,
            "title_clean": title_clean,
            "company_raw": company_raw,
            "company_clean": company_clean,
            "location_raw": loc_raw,
            "location_city": city,
            "location_gov": gov,
            "salary_min": salary_info['min'],
            "salary_max": salary_info['max'],
            "salary_currency": salary_info['currency'],
            "experience_years_min": None, # Wuzzuf needs inner page scraping for this
            "experience_years_max": None,
            "source": self.source_name,
            "job_url": record.get('job_url', ''),
            "scraped_at": record.get('scraped_at'),
            "posted_at": record.get('scraped_at')[:10], # Wuzzuf list has no post_date
            "run_id": record.get('run_id'),
            "is_remote": "remote" in loc_raw.lower() or "remote" in title_raw.lower()
        }
        return processed
