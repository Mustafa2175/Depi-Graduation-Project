import subprocess
import os
import sys

def run_scraper(script_path):
    print(f"🚀 Starting scraper: {script_path}...")
    try:
        # Run the script and wait for it to finish
        result = subprocess.run([sys.executable, script_path], check=True)
        if result.returncode == 0:
            print(f"✅ Finished {script_path} successfully.\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while running {script_path}: {e}\n")

def main():
    # List of all scraper scripts
    scrapers = [
        "scraping/Wuzzuf (1).py",
        "scraping/bayt.py",
        "scraping/indeed.py",
        "scraping/forasna.py",
        "scraping/jobzella.py"
    ]

    print("🌟 Starting NileTech Pulse Master Scraper 🌟\n")
    print("="*40)

    for scraper in scrapers:
        if os.path.exists(scraper):
            run_scraper(scraper)
        else:
            print(f"⚠️ Warning: Scraper file not found: {scraper}")

    print("="*40)
    print("🏁 All scraping tasks are complete!")

if __name__ == "__main__":
    main()
