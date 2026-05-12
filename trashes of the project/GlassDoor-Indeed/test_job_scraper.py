import sys
from unittest.mock import MagicMock, patch
import unittest
import pandas as pd

# Mock modules before importing job_scraper
mock_jobspy = MagicMock()
sys.modules["jobspy"] = mock_jobspy
mock_airflow = MagicMock()
sys.modules["airflow"] = mock_airflow
sys.modules["airflow.operators"] = MagicMock()
sys.modules["airflow.operators.python"] = MagicMock()

# Import the functions to test
from producers.job_scraper import safe_str, safe_float, extract_salary, row_to_dict, scrape_all_terms

class TestJobScraper(unittest.TestCase):
    def test_safe_str(self):
        self.assertEqual(safe_str("  hello  "), "hello")
        self.assertIsNone(safe_str(""))
        self.assertIsNone(safe_str(None))
        self.assertIsNone(safe_str(float('nan')))

    def test_safe_float(self):
        self.assertEqual(safe_float("123.45"), 123.45)
        self.assertEqual(safe_float(123), 123.0)
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float("abc"))
        self.assertIsNone(safe_float(float('nan')))

    def test_extract_salary(self):
        row = {
            "min_amount": 1000,
            "max_amount": 2000,
            "currency": "USD",
            "interval": "monthly"
        }
        expected = {
            "min": 1000.0,
            "max": 2000.0,
            "currency": "USD",
            "interval": "monthly"
        }
        self.assertEqual(extract_salary(row), expected)

        row_none = {"min_amount": None, "max_amount": None}
        self.assertIsNone(extract_salary(row_none))

    def test_row_to_dict(self):
        row = {
            "title": "Engineer",
            "company": "Tech Corp",
            "location": "Cairo",
            "min_amount": 1000,
            "description": "A very long description" * 100,
            "job_url": "http://example.com"
        }
        result = row_to_dict(row)
        self.assertEqual(result["title"], "Engineer")
        self.assertEqual(len(result["description"]), 500)
        self.assertEqual(result["salary"]["min"], 1000.0)

    @patch("producers.job_scraper.scrape_jobs")
    def test_scrape_all_terms(self, mock_scrape):
        # Mock dataframe
        df = pd.DataFrame([{
            "title": "Software Engineer",
            "company": "Company A",
            "job_url": "http://job1.com",
            "site": "indeed"
        }])
        mock_scrape.return_value = df
        
        jobs = scrape_all_terms()
        
        self.assertTrue(len(jobs) > 0)
        self.assertEqual(jobs[0]["title"], "Software Engineer")
        self.assertTrue(mock_scrape.called)

if __name__ == "__main__":
    unittest.main()
