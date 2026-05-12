import abc
import json
import os
from typing import List, Dict
from datetime import datetime
import hashlib
from processing.core.schema import JobSchema

class BaseProcessor(abc.ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name

    def load_raw_data(self, file_path: str) -> List[Dict]:
        """Loads JSON data from the raw directory."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_job_hash(self, title: str, company: str, location: str) -> str:
        """Simple deduplication hash: normalized_title + company + location."""
        combined = f"{title.lower().strip()}|{company.lower().strip()}|{location.lower().strip()}"
        return hashlib.md5(combined.encode()).hexdigest()

    @abc.abstractmethod
    def process_record(self, record: Dict) -> JobSchema:
        """Each source must implement its own record mapping."""
        pass

    def run(self, input_path: str) -> List[JobSchema]:
        """The main orchestration loop for a single file."""
        raw_data = self.load_raw_data(input_path)
        processed_data = []
        
        for record in raw_data:
            try:
                clean_record = self.process_record(record)
                processed_data.append(clean_record)
            except Exception as e:
                # Log error and skip bad record (Quality Gate)
                print(f"Error processing record from {self.source_name}: {e}")
                
        return processed_data
