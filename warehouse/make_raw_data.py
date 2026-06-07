"""Generate realistic Bronze (raw) JSON for an end-to-end pipeline test.

Writes data/raw/<source>/<date>/<file>.json in the shape each scraper
produces, including free-text `description` / `requirements` so the
cleaning layer's skill extractor and job-type classifiers have something
to work on. The set includes:

* skill keywords that appear ONLY in the description (not the title) —
  proving extraction reads descriptions, e.g. Airflow/dbt for a
  "Data Engineer" role
* remote / hybrid / part-time / internship wording for classification
* a cross-source duplicate (same title+company+location on Wuzzuf & Bayt)
* two intentionally invalid records to exercise the quality gate
"""
import json
import os
import random
from datetime import date, timedelta

random.seed(7)


def _raw_root() -> str:
    # read live so test isolation (RAW_DIR override) takes effect
    return os.getenv("RAW_DIR", "data/raw")

SCRAPED = (date.today() - timedelta(days=1)).isoformat() + "T10:00:00"

# (title, description-with-skills, work/employment wording)
JOB_TEMPLATES = [
    ("Senior Data Engineer",
     "Build ETL pipelines with Python and Airflow, transform data using dbt, "
     "process big data on Spark and load into PostgreSQL.", "remote"),
    ("Data Analyst",
     "Strong SQL and Excel skills, build dashboards in Power BI and Tableau.", "hybrid"),
    ("Machine Learning Engineer",
     "Develop models with Python, TensorFlow and PyTorch. Deep learning experience required.",
     "on-site"),
    ("Backend Developer",
     "Design REST APIs with Django, deploy with Docker, manage PostgreSQL databases.",
     "full-time"),
    ("Node.js Developer",
     "Build services with Node.js and JavaScript, MongoDB experience, GraphQL a plus.",
     "remote"),
    (".NET Developer",
     "Develop enterprise apps with C# and .NET, SQL Server backend.", "on-site"),
    ("React Frontend Developer",
     "Build UIs with React, TypeScript and modern JavaScript.", "hybrid"),
    ("DevOps Engineer",
     "Manage Kubernetes clusters on AWS, automate with Terraform and Docker on Linux.",
     "remote"),
    ("QA Automation Engineer",
     "Write automated tests in Python, manage pipelines with Git.", "part-time"),
    ("Java Backend Developer (Internship)",
     "Learn Java and Spring framework, work with PostgreSQL. Internship opportunity.",
     "internship"),
    ("Business Intelligence Analyst",
     "Develop reports in Power BI, advanced SQL and Excel modelling.", "full-time"),
    ("Flutter Mobile Developer",
     "Cross-platform apps with Flutter, integrate REST APIs.", "contract"),
]

COMPANIES = ["Fawry", "Vodafone", "Instabug", "Paymob", "Robusta", "Halan", "Breadfast"]
LOCATIONS = ["Maadi, Cairo", "Nasr City, Cairo", "Dokki, Giza", "Smouha, Alexandria",
             "6th of October, Giza", "Mansoura", "New Cairo, Cairo"]
SALARIES = ["EGP 15,000 - 25,000", "EGP 20,000 - 35,000", "$1500 - $2500", "", "Confidential"]


def base_record(source, idx, title, desc, mode, **extra):
    """Build a record in the producer contract shape (producers.contract)."""
    rec = {
        "job_id": f"{source}-{idx}",
        "title": title,
        "company": random.choice(COMPANIES),
        "location": random.choice(LOCATIONS),
        "salary": "",
        "description": desc + f"  This is a {mode} position.",
        "experience": "",
        "posted_at_raw": "",
        "industry": "",
        "job_url": f"https://{source}.example.com/job/{idx}",
        "source": source,
        "scraped_at": SCRAPED,
        "run_id": f"{source}-run-1",
    }
    rec.update(extra)
    return rec


def write_json(source, day_iso, records, suffix=""):
    out_dir = os.path.join(_raw_root(), source, day_iso)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{source}_{day_iso}{suffix}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  wrote {len(records):2d} raw records -> {path}")


def main():
    day = (date.today() - timedelta(days=1)).isoformat()
    print("Generating raw (Bronze) data...")

    # Wuzzuf
    recs = []
    for i in range(8):
        t, d, m = random.choice(JOB_TEMPLATES)
        recs.append(base_record("wuzzuf", i, t, d, m, salary=random.choice(SALARIES)))
    write_json("wuzzuf", day, recs)

    # Bayt (has experience + post_date)
    recs = []
    for i in range(8):
        t, d, m = random.choice(JOB_TEMPLATES)
        recs.append(base_record("bayt", i, t, d, m,
                                salary=random.choice(SALARIES),
                                experience=random.choice(["2-5 Years", "5-10 Years", ""]),
                                posted_at_raw=random.choice(["3 days ago", "1 week ago", "2 hours ago"])))
    write_json("bayt", day, recs)

    # Indeed (date_posted)
    recs = []
    for i in range(7):
        t, d, m = random.choice(JOB_TEMPLATES)
        recs.append(base_record("indeed", i, t, d, m,
                                salary=random.choice(SALARIES),
                                posted_at_raw=day + "T08:00:00"))
    write_json("indeed", day, recs)

    # Forasna (no salary)
    recs = []
    for i in range(6):
        t, d, m = random.choice(JOB_TEMPLATES)
        recs.append(base_record("forasna", i, t, d, m))
    write_json("forasna", day, recs)

    # Jobzella
    recs = []
    for i in range(6):
        t, d, m = random.choice(JOB_TEMPLATES)
        recs.append(base_record("jobzella", i, t, d, m, salary=random.choice(SALARIES)))
    write_json("jobzella", day, recs)

    # --- Cross-source duplicate: identical title+company+location on two
    #     sources that clean titles the same way -> same job_hash. The skills
    #     (Airflow/dbt/Spark) live only in the description.
    dup_title = "Senior Data Engineer"
    dup_desc = ("Build ETL pipelines with Python and Airflow, transform data using dbt, "
                "process big data on Spark, store in PostgreSQL.")
    for src in ("wuzzuf", "bayt"):
        rec = base_record(src, "DUP", dup_title, dup_desc, "remote",
                          salary="EGP 40,000 - 55,000")
        rec["company"] = "Fawry"
        rec["location"] = "Maadi, Cairo"
        if src == "bayt":
            rec["posted_at_raw"] = "2 days ago"
        write_json(src, date.today().isoformat(), [rec], suffix="_dup")

    # --- Two invalid records for the quality gate (Wuzzuf):
    #     (1) missing title  (2) empty job_url
    bad = [
        base_record("wuzzuf", "BAD1", "", "Some description", "on-site",
                    salary="EGP 10,000 - 12,000"),
        {**base_record("wuzzuf", "BAD2", "Random Role", "desc", "on-site",
                       salary="EGP 9,000 - 11,000"), "job_url": ""},
    ]
    write_json("wuzzuf", date.today().isoformat(), bad, suffix="_bad")
    print("Done.")


if __name__ == "__main__":
    main()
