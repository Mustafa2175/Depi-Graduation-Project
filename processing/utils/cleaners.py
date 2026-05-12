import re
from bs4 import BeautifulSoup

def clean_text(text: str) -> str:
    """Removes extra whitespaces, emojis, and special symbols."""
    if not text:
        return ""
    # Remove HTML if present
    text = BeautifulSoup(text, "html.parser").get_text()
    # Remove special chars but keep basic punctuation
    text = re.sub(r'[^\w\s\-\.\(\)\/\,]', '', text)
    # Standardize whitespace
    text = " ".join(text.split())
    return text.strip()

def strip_noise_from_title(title: str) -> str:
    """Removes common hiring noise from job titles."""
    noise = [r'\(.*\)', r'\[.*\]', r'urgent', r'hiring', r'immediate', r'remote', r'hybrid']
    for pattern in noise:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    return clean_text(title)
