"""Generate realistic Silver-layer CSVs for testing Phase 4 without live scraping.

Writes files to data/silver/<source>/<date>/<file>.csv exactly as the real
processing pipeline (processing/main.py) does — same 20 columns, same
utf-8-sig encoding. The generated set deliberately exercises edge cases:

* cross-source duplicates (identical job_hash from two boards)
* remote / on-site mix
* missing salaries and experience
* a company whose raw name changes between runs (to exercise SCD Type 2)
* a variety of titles spanning multiple categories and skills
"""
import csv
import hashlib
import os
import random
from datetime import date, timedelta

from processing.core.schema import JobSchema  # noqa: F401  (documents the contract)

random.seed(42)


def _silver_root() -> str:
    # read live so test isolation (SILVER_DIR override) takes effect
    return os.getenv("SILVER_DIR", "data/silver")

CITIES = [
    ("Nasr City", "Cairo"), ("Maadi", "Cairo"), ("New Cairo", "Cairo"),
    ("Heliopolis", "Cairo"), ("6th of October", "Giza"), ("Dokki", "Giza"),
    ("Mohandessin", "Giza"), ("Sheikh Zayed", "Giza"), ("Smouha", "Alexandria"),
    ("Alexandria", "Alexandria"), ("Mansoura", "Dakahlia"), ("Tanta", "Gharbia"),
    ("Unknown", "Egypt"),
]

TITLES = [
    "Senior Python Data Engineer", "Data Engineer (Airflow, dbt)",
    "Junior Data Analyst", "Machine Learning Engineer", "Data Scientist",
    "Backend Developer (Django)", "Node.js Backend Engineer", ".NET Developer",
    "Laravel PHP Developer", "React Frontend Developer", "Angular Developer",
    "Full Stack MERN Developer", "Flutter Mobile Developer", "Android Developer",
    "DevOps Engineer (AWS, Kubernetes)", "Cloud Engineer (Azure)",
    "QA Automation Engineer", "Manual QA Tester", "Cybersecurity Analyst",
    "Database Administrator (PostgreSQL)", "UI/UX Product Designer",
    "IT Support Specialist", "Network Engineer", "Project Manager",
    "Scrum Master", "Senior Java Spring Developer", "Golang Backend Developer",
    "Business Intelligence Analyst (Power BI)", "Site Reliability Engineer",
    "TypeScript Frontend Engineer",
]

COMPANIES = [
    "Vodafone Egypt", "Fawry", "Instabug", "Swvl", "Paymob", "Robusta",
    "Incorta", "Halan", "Breadfast", "ITWorx", "Raya", "Etisalat Misr",
]

CURRENCIES = ["EGP", "USD", None]
SOURCES = ["wuzzuf", "bayt", "indeed", "forasna", "jobzella"]

# Plausible skill sets keyed by a substring of the title (mimics what the
# cleaning layer's skill extractor would emit into the Silver `skills` column).
SKILL_POOL = {
    "Data Engineer": ["Python", "SQL", "Airflow", "dbt", "Spark"],
    "Data Analyst": ["SQL", "Excel", "Power BI", "Tableau"],
    "Data Scientist": ["Python", "Machine Learning", "Pandas", "PyTorch"],
    "Machine Learning": ["Python", "TensorFlow", "PyTorch", "Machine Learning"],
    "Backend": ["Python", "Django", "PostgreSQL", "Docker"],
    "Node": ["Node.js", "JavaScript", "MongoDB", "REST API"],
    ".NET": [".NET", "C#", "SQL Server"],
    "Laravel": ["PHP", "Laravel", "MySQL"],
    "React": ["React", "JavaScript", "TypeScript"],
    "Angular": ["Angular", "TypeScript"],
    "Full Stack": ["React", "Node.js", "MongoDB", "TypeScript"],
    "Flutter": ["Flutter", "Dart"],
    "Android": ["Kotlin", "Java"],
    "DevOps": ["Docker", "Kubernetes", "AWS", "Terraform", "Linux"],
    "Cloud": ["Azure", "Docker", "Kubernetes"],
    "QA": ["Python", "Git"],
    "Cybersecurity": ["Linux", "Python"],
    "Database Administrator": ["PostgreSQL", "SQL", "Oracle"],
    "Java Spring": ["Java", "Spring", "PostgreSQL"],
    "Golang": ["Go", "Docker", "Kubernetes"],
    "Business Intelligence": ["Power BI", "SQL", "Excel"],
    "Site Reliability": ["Kubernetes", "AWS", "Terraform", "Linux"],
    "TypeScript": ["TypeScript", "React"],
}
WORK_MODES = ["on-site", "on-site", "on-site", "hybrid", "remote"]
EMPLOYMENT_TYPES = ["full-time", "full-time", "full-time", "part-time", "contract", "internship"]


def skills_for(title):
    for key, skills in SKILL_POOL.items():
        if key.lower() in title.lower():
            return "|".join(skills)
    return ""


def job_hash(title, company, city):
    return hashlib.md5(f"{title}|{company}|{city}".encode("utf-8")).hexdigest()


def make_record(source, idx, run_id, posted, scraped):
    title = random.choice(TITLES)
    company = random.choice(COMPANIES)
    city, gov = random.choice(CITIES)
    work_mode = random.choice(WORK_MODES)
    employment_type = random.choice(EMPLOYMENT_TYPES)
    is_remote = work_mode == "remote"

    if random.random() < 0.55:
        smin = random.choice([8000, 12000, 15000, 20000, 25000, 30000])
        smax = smin + random.choice([3000, 5000, 10000, 15000])
        currency = random.choice(CURRENCIES) or "EGP"
    else:
        smin = smax = ""
        currency = ""

    exp_min = random.choice(["", 0, 1, 2, 3, 5])
    exp_max = (exp_min + random.choice([1, 2, 3])) if isinstance(exp_min, int) and exp_min != "" else ""

    return {
        "job_id": f"{source}-{idx}",
        "job_hash": job_hash(title, company, city),
        "title_raw": title,
        "title_clean": title,
        "company_raw": company,
        "company_clean": company.replace(" Egypt", "").replace(" Misr", "").strip(),
        "location_raw": f"{city}, {gov}, Egypt",
        "location_city": city,
        "location_gov": gov,
        "salary_min": smin,
        "salary_max": smax,
        "salary_currency": currency,
        "salary_period": "monthly" if currency else "",
        "experience_years_min": exp_min,
        "experience_years_max": exp_max,
        "skills": skills_for(title),
        "work_mode": work_mode,
        "employment_type": employment_type,
        "source": source,
        "job_url": f"https://{source}.example.com/job/{idx}",
        "scraped_at": scraped.isoformat() + "T10:00:00",
        "posted_at": posted.isoformat(),
        "run_id": run_id,
        "is_remote": is_remote,
    }


FIELDS = list(make_record("wuzzuf", 0, "x", date.today(), date.today()).keys())


def write_csv(source, day: date, records, suffix=""):
    out_dir = os.path.join(_silver_root(), source, day.isoformat())
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{source}_{day.isoformat()}{suffix}.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(records)
    print(f"  wrote {len(records):3d} rows -> {path}")


def main():
    today = date.today()
    print("Generating sample Silver data...")

    # Day 1: one file per source.
    for source in SOURCES:
        n = random.randint(12, 20)
        recs = [make_record(source, i, f"{source}-run-1",
                            today - timedelta(days=random.randint(0, 14)),
                            today - timedelta(days=1))
                for i in range(n)]
        write_csv(source, today - timedelta(days=1), recs)

    # Cross-source duplicate: same posting appears on wuzzuf and bayt
    # (identical job_hash) — must collapse to a single fact row.
    dup_title, dup_company, dup_city = "Senior Python Data Engineer", "Fawry", "Maadi"
    dup_hash = job_hash(dup_title, dup_company, dup_city)
    dup_common = {
        "job_hash": dup_hash, "title_raw": dup_title, "title_clean": dup_title,
        "company_raw": dup_company, "company_clean": dup_company,
        "location_raw": "Maadi, Cairo, Egypt", "location_city": dup_city,
        "location_gov": "Cairo", "salary_min": 40000, "salary_max": 55000,
        "salary_currency": "EGP", "salary_period": "monthly",
        "experience_years_min": 5, "experience_years_max": 8,
        "skills": "Python|SQL|Airflow|dbt|Spark", "work_mode": "remote",
        "employment_type": "full-time",
        "scraped_at": (today - timedelta(days=1)).isoformat() + "T10:00:00",
        "posted_at": (today - timedelta(days=3)).isoformat(),
        "is_remote": True,
    }
    for src in ("wuzzuf", "bayt"):
        rec = dict(dup_common, job_id=f"{src}-DUP", source=src,
                   job_url=f"https://{src}.example.com/job/DUP", run_id=f"{src}-run-1")
        write_csv(src, today, [rec], suffix="_dup")

    # Day 2 (today): a fresh file — exercises incremental loading. Includes an
    # SCD2 trigger: "Fawry" now reports a different raw name.
    recs = [make_record("wuzzuf", 1000 + i, "wuzzuf-run-2",
                        today - timedelta(days=random.randint(0, 3)), today)
            for i in range(10)]
    # SCD2 trigger: same company_clean ("Fawry") but a changed raw name ->
    # the loader should close the old dim_company row and open a new version.
    scd2 = make_record("wuzzuf", 9999, "wuzzuf-run-2", today, today)
    scd2.update(company_clean="Fawry", company_raw="Fawry for Banking Technology")
    recs.append(scd2)
    write_csv("wuzzuf", today, recs)

    print("Done.")


if __name__ == "__main__":
    main()
