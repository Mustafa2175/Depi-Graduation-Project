import pandas as pd
from datetime import datetime
import os

class DataValidator:
    REQUIRED_COLUMNS = [
        'job_id', 'job_hash', 'title_clean', 'company_clean', 
        'location_city', 'location_gov', 'source', 'job_url', 
        'scraped_at', 'posted_at', 'run_id'
    ]

    @staticmethod
    def check_schema(df: pd.DataFrame) -> list:
        """Returns missing columns if any."""
        missing = [col for col in DataValidator.REQUIRED_COLUMNS if col not in df.columns]
        return missing

    @staticmethod
    def validate_row(row) -> list:
        """Performs deep validation on a single row. Returns list of error messages."""
        errors = []
        
        # 1. Null Checks
        for col in DataValidator.REQUIRED_COLUMNS:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                errors.append(f"Missing required field: {col}")

        # 2. Date Logic
        try:
            posted_date = datetime.strptime(str(row['posted_at']), '%Y-%m-%d')
            if posted_date > datetime.now():
                errors.append("Posted date is in the future")
        except:
            errors.append("Invalid date format in posted_at")

        # 3. Salary Logic
        if not pd.isna(row['salary_min']) and not pd.isna(row['salary_max']):
            if float(row['salary_max']) < float(row['salary_min']):
                errors.append("salary_max is less than salary_min")

        # 4. URL Logic
        if not str(row['job_url']).startswith('http'):
            errors.append("Invalid job_url format")

        return errors
