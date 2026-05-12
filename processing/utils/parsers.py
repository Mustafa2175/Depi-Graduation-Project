import re
from datetime import datetime, timedelta

def parse_salary(salary_str: str) -> dict:
    """
    Extracts min and max salary from strings like 'EGP 15,000 - 20,000'.
    Returns: {'min': float, 'max': float, 'currency': str}
    """
    result = {'min': None, 'max': None, 'currency': 'EGP'}
    
    if not salary_str or salary_str.lower() in ['n/a', 'confidential']:
        return result

    # Identify currency
    if '$' in salary_str or 'USD' in salary_str.upper():
        result['currency'] = 'USD'
    
    # Extract numbers
    numbers = re.findall(r'[\d\.]+', salary_str.replace(',', ''))
    numbers = [float(n) for n in numbers if n]
    
    if len(numbers) >= 2:
        result['min'], result['max'] = numbers[0], numbers[1]
    elif len(numbers) == 1:
        result['min'] = result['max'] = numbers[0]
        
    return result

def parse_posted_date(posted_str: str, scraped_at_iso: str) -> str:
    """
    Converts relative dates like '3 days ago' to YYYY-MM-DD.
    """
    scraped_at = datetime.fromisoformat(scraped_at_iso)
    posted_str = posted_str.lower()
    
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
