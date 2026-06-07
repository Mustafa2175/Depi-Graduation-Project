import re
from datetime import datetime, timedelta

def parse_salary_period(salary_str: str):
    """Detect the pay period from a salary string.

    Returns one of 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly',
    or None when no period is stated. Handles English and common Arabic terms.
    """
    if not salary_str:
        return None
    s = salary_str.lower()
    if 'hour' in s or 'ساعة' in s or '/hr' in s or 'hourly' in s:
        return 'hourly'
    if 'year' in s or 'annum' in s or 'annual' in s or 'سنة' in s or 'سنوي' in s or '/yr' in s:
        return 'yearly'
    if 'week' in s or 'أسبوع' in s or 'weekly' in s:
        return 'weekly'
    if 'day' in s or 'يوم' in s or 'daily' in s:
        return 'daily'
    if 'month' in s or 'شهر' in s or '/mo' in s or 'monthly' in s:
        return 'monthly'
    return None


def parse_salary(salary_str: str) -> dict:
    """
    Extracts min, max, currency and pay period from strings like
    'EGP 15,000 - 20,000 / month'.
    Returns: {'min': float, 'max': float, 'currency': str, 'period': str|None}
    """
    result = {'min': None, 'max': None, 'currency': 'EGP', 'period': None}

    if not salary_str or salary_str.lower() in ['n/a', 'confidential']:
        return result

    # Identify currency
    if '$' in salary_str or 'USD' in salary_str.upper():
        result['currency'] = 'USD'

    result['period'] = parse_salary_period(salary_str)

    # Extract numbers (ignore the digits inside period tokens like "/mo24")
    numbers = re.findall(r'[\d\.]+', salary_str.replace(',', ''))
    numbers = [float(n) for n in numbers if n]

    if len(numbers) >= 2:
        result['min'], result['max'] = numbers[0], numbers[1]
    elif len(numbers) == 1:
        result['min'] = result['max'] = numbers[0]

    return result

def parse_experience(exp_str: str):
    """Extract (min_years, max_years) from strings like '5 - 15 Years'.

    Returns (None, None) when no digits are present. A single number is
    treated as the minimum.
    """
    if not exp_str:
        return None, None
    nums = [int(n) for n in re.findall(r"\d+", str(exp_str))]
    # ignore implausible values (e.g. years like 2024 leaking in)
    nums = [n for n in nums if n <= 50]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], None
    return nums[0], nums[1]


def parse_posted_date(posted_str: str, scraped_at_iso: str) -> str:
    """
    Converts a posted date to YYYY-MM-DD.

    Handles both relative dates ('3 days ago') and absolute ISO-ish dates
    ('2026-06-01', '2026-06-01T..'); falls back to the scrape date.
    """
    scraped_at = datetime.fromisoformat(scraped_at_iso)
    posted_str = (posted_str or "").strip().lower()

    # Absolute date already in YYYY-MM-DD form (e.g. Indeed's date_posted).
    abs_match = re.match(r"(\d{4}-\d{2}-\d{2})", posted_str)
    if abs_match:
        return abs_match.group(1)

    if 'hour' in posted_str:
        hours = int(re.search(r'\d+', posted_str).group())
        return (scraped_at - timedelta(hours=hours)).strftime('%Y-%m-%d')
    elif 'day' in posted_str:
        days = int(re.search(r'\d+', posted_str).group())
        return (scraped_at - timedelta(days=days)).strftime('%Y-%m-%d')
    elif 'week' in posted_str:
        weeks = int(re.search(r'\d+', posted_str).group())
        return (scraped_at - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    elif 'month' in posted_str:
        months = int(re.search(r'\d+', posted_str).group())
        return (scraped_at - timedelta(days=months*30)).strftime('%Y-%m-%d')
    
    return scraped_at.strftime('%Y-%m-%d')
