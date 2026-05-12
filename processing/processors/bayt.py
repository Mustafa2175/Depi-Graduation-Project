from processing.core.base import BaseProcessor
from processing.utils import mappings, cleaners, parsers
from processing.core.schema import JobSchema
from typing import Dict

class BaytProcessor(BaseProcessor):
    def __init__(self):
        super().__init__(source_name="bayt")

    def process_record(self, record: Dict) -> JobSchema:
        # 1. Clean basic fields
        title_raw = record.get('title', '')
        title_clean = cleaners.strip_noise_from_title(title_raw)
        company_raw = record.get('company', 'Confidential')
        company_clean = cleaners.clean_text(company_raw)
        
        # 2. Location Normalization
        loc_raw = record.get('location', '')
        city, gov = mappings.normalize_location(loc_raw)
        
        # 3. Salary Parsing
        salary_info = parsers.parse_salary(record.get('salary', ''))
        
        # 4. Experience Parsing (Custom for Bayt if needed)
        # Bayt sample: "Management·5-15 Years of Experience"
        exp_str = record.get('experience', '')
        exp_nums = [int(s) for s in str(exp_str).replace('-', ' ').split() if s.isdigit()]
        exp_min = exp_nums[0] if len(exp_nums) > 0 else None
        exp_max = exp_nums[1] if len(exp_nums) > 1 else None

        # 5. Build Unified Schema
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
            "experience_years_min": exp_min,
            "experience_years_max": exp_max,
            "source": self.source_name,
            "job_url": record.get('job_url', ''),
            "scraped_at": record.get('scraped_at'),
            "posted_at": parsers.parse_posted_date(record.get('post_date', ''), record.get('scraped_at')),
            "run_id": record.get('run_id'),
            "is_remote": "remote" in loc_raw.lower() or "remote" in title_raw.lower()
        }
        
        return processed
