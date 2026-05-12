from processing.core.base import BaseProcessor
from processing.utils import mappings, cleaners, parsers
from processing.core.schema import JobSchema
from typing import Dict

class IndeedProcessor(BaseProcessor):
    def __init__(self):
        super().__init__(source_name="indeed")

    def process_record(self, record: Dict) -> JobSchema:
        title_raw = record.get('title', '')
        title_clean = cleaners.strip_noise_from_title(title_raw)
        company_clean = cleaners.clean_text(record.get('company', ''))
        
        # Indeed location can be Arabic like "القاهرة الجديدة"
        loc_raw = record.get('location', '')
        city, gov = mappings.normalize_location(loc_raw)
        
        salary_info = parsers.parse_salary(record.get('salary', ''))
        
        processed: JobSchema = {
            "job_id": record.get('job_id'),
            "job_hash": self.generate_job_hash(title_clean, company_clean, city),
            "title_raw": title_raw,
            "title_clean": title_clean,
            "company_raw": record.get('company', ''),
            "company_clean": company_clean,
            "location_raw": loc_raw,
            "location_city": city,
            "location_gov": gov,
            "salary_min": salary_info['min'],
            "salary_max": salary_info['max'],
            "salary_currency": salary_info['currency'],
            "experience_years_min": None,
            "experience_years_max": None,
            "source": self.source_name,
            "job_url": record.get('job_url', ''),
            "scraped_at": record.get('scraped_at'),
            "posted_at": record.get('date_posted', record.get('scraped_at'))[:10],
            "run_id": record.get('run_id'),
            "is_remote": "remote" in loc_raw.lower() or "remote" in title_raw.lower()
        }
        return processed
