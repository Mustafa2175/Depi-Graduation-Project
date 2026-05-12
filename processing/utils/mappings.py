# Final comprehensive mapping for Egyptian cities (Arabic & English)
LOCATION_MAP = {
    # English Keys
    "nasr city": ("Nasr City", "Cairo"),
    "maadi": ("Maadi", "Cairo"),
    "new cairo": ("New Cairo", "Cairo"),
    "heliopolis": ("Heliopolis", "Cairo"),
    "6th of october": ("6th of October", "Giza"),
    "sheikh zayed": ("Sheikh Zayed", "Giza"),
    "dokki": ("Dokki", "Giza"),
    "mohandessin": ("Mohandessin", "Giza"),
    "faisal": ("Faisal", "Giza"),
    "haram": ("Haram", "Giza"),
    "sheraton": ("Sheraton", "Cairo"),
    "mokattam": ("Mokattam", "Cairo"),
    "obour": ("Obour City", "Cairo"),
    "10th of ramadan": ("10th of Ramadan", "Sharqia"),
    "smouha": ("Smouha", "Alexandria"),
    "alexandria": ("Alexandria", "Alexandria"),
    "cairo": ("Cairo", "Cairo"),
    "giza": ("Giza", "Giza"),
    "mansoura": ("Mansoura", "Dakahlia"),
    "tanta": ("Tanta", "Gharbia"),
    
    # Arabic Keys (For Forasna, Indeed, etc.)
    "نصر": ("Nasr City", "Cairo"),
    "معادي": ("Maadi", "Cairo"),
    "مصر الجديدة": ("Heliopolis", "Cairo"),
    "أكتوبر": ("6th of October", "Giza"),
    "شيخ زايد": ("Sheikh Zayed", "Giza"),
    "دقي": ("Dokki", "Giza"),
    "مهندسين": ("Mohandessin", "Giza"),
    "فيصل": ("Faisal", "Giza"),
    "هرم": ("Haram", "Giza"),
    "شيراتون": ("Sheraton", "Cairo"),
    "مقطم": ("Mokattam", "Cairo"),
    "عبور": ("Obour City", "Cairo"),
    "رمضان": ("10th of Ramadan", "Sharqia"),
    "سموحة": ("Smouha", "Alexandria"),
    "إسكندرية": ("Alexandria", "Alexandria"),
    "قاهرة": ("Cairo", "Cairo"),
    "جيزة": ("Giza", "Giza"),
    "منصورة": ("Mansoura", "Dakahlia"),
    "طنطا": ("Tanta", "Gharbia"),
    "شبرا": ("Shubra", "Cairo"),
}

def normalize_location(location_str: str) -> tuple:
    if not location_str:
        return "Unknown", "Egypt"
        
    loc_lower = location_str.lower()
    
    for key, (city, gov) in LOCATION_MAP.items():
        if key in loc_lower:
            return city, gov
            
    # Language independent fallbacks
    if "cairo" in loc_lower or "قاهرة" in loc_lower: return "Cairo", "Cairo"
    if "giza" in loc_lower or "جيزة" in loc_lower: return "Giza", "Giza"
    
    return "Unknown", "Egypt"
