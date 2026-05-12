import json
import time
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_bayt_jobs(base_url="https://www.bayt.com/en/egypt/jobs/"):
    jobs_data = []
    
    # إعداد المتصفح باستخدام undetected-chromedriver لتخطي Cloudflare
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new") # استخدام المتصفح المرئي لتخطي Cloudflare بسهولة
    options.add_argument("--window-size=1920,1080")
    
    print("Starting browser...")
    driver = uc.Chrome(options=options, version_main=147)
    
    page_num = 1
    max_pages = 10 # الحد الأقصى للصفحات لتجنب الحظر
    
    try:
        while page_num <= max_pages:
            url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
            print(f"Navigating to {url} ...")
            
            driver.get(url)
            
            # ننتظر قليلاً لنتأكد من تخطي Cloudflare وتحميل الصفحة
            time.sleep(5)
            
            # التأكد من تحميل العناصر عبر انتظار ظهور الوظائف
            try:
                print("Waiting for page load... Please solve the Cloudflare Captcha if it appears.")
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.has-pointer-d"))
                )
            except:
                print("Could not find job listings after 60 seconds, page might be blocked or empty.")
            
            # جلب محتوى الصفحة كـ HTML
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            
            job_cards = soup.select("li.has-pointer-d")
            count = len(job_cards)
            
            if count == 0:
                print("No more jobs found. Exiting pagination.")
                break
                
            print(f"Found {count} jobs on page {page_num}.")
            
            for card in job_cards:
                try:
                    # استخراج عنوان الوظيفة
                    title_elem = card.select_one("h2 a")
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    # استخراج رابط الوظيفة
                    link = title_elem.get("href") if title_elem else ""
                    if link and not link.startswith("http"):
                        link = "https://www.bayt.com" + link
                        
                    # استخراج اسم الشركة
                    company_elem = card.select_one("div.job-company-location-wrapper > a, div.job-company-location-wrapper > b")
                    company = company_elem.text.strip() if company_elem else "N/A"
                    
                    # استخراج الموقع
                    location_elems = card.select("div.t-mute.t-small a.t-mute")
                    location = ", ".join([loc.text.strip() for loc in location_elems])
                    
                    # استخراج الوصف
                    desc_elem = card.select_one("div.jb-descr")
                    description = desc_elem.text.strip().replace("Summary: \n", "").strip() if desc_elem else "N/A"
                    
                    # استخراج الراتب (إن وجد)
                    salary_elem = card.select_one("dt.jb-label-salary")
                    salary = salary_elem.text.strip() if salary_elem else "Not Disclosed"
                    
                    # استخراج الخبرة والمستوى المهني
                    exp_elem = card.select_one("dt.jb-label-careerlevel")
                    experience = exp_elem.text.strip().replace(" · ", " - ") if exp_elem else "N/A"
                    
                    # استخراج تاريخ النشر
                    date_elem = card.select_one("div.jb-date span")
                    post_date = date_elem.text.strip() if date_elem else "N/A"
                    
                    job_info = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary": salary,
                        "experience": experience,
                        "post_date": post_date,
                        "description": description,
                        "link": link
                    }
                    jobs_data.append(job_info)
                except Exception as e:
                    print(f"Error extracting a job: {e}")
            
            page_num += 1
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving collected data so far...")
    finally:
        driver.quit()
        
    return jobs_data

if __name__ == "__main__":
    print("Starting Bayt.com scraper...")
    jobs = scrape_bayt_jobs("https://www.bayt.com/en/egypt/jobs/")
    
    if jobs:
        output_file = "bayt_jobs.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=4)
        print(f"\nSuccessfully saved {len(jobs)} jobs to {output_file}")
    else:
        print("\nNo jobs were scraped. The site might be blocking the request.")
