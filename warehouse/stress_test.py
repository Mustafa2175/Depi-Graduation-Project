"""High-volume stress test for the warehouse + dbt layers.

Generates a large Silver dataset (default 20,000 postings, configurable via
STRESS_ROWS) with realistic cardinality and a meaningful share of duplicates,
then:

  1. loads it into the star schema and measures throughput
  2. asserts correctness at scale (dedup, FK integrity, NOT NULL keys)
  3. re-loads to confirm idempotency holds under volume
  4. runs `dbt build` on the large dataset and checks the marts populate

    export PYTHONPATH=$PYTHONPATH:.
    python3 warehouse/stress_test.py           # 20k rows
    STRESS_ROWS=50000 python3 warehouse/stress_test.py

Exit code 0 = all checks passed.
"""
import csv
import hashlib
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import date, timedelta

import psycopg2

from warehouse import config
from warehouse.isolation import isolated_workspace
from warehouse.load_to_postgres import WarehouseLoader

ROWS = int(os.getenv("STRESS_ROWS", "20000"))
random.seed(2024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBT_DIR = os.path.join(ROOT, "dbt", "job_market_tracker")

SOURCES = ["wuzzuf", "bayt", "indeed", "forasna", "jobzella"]
TITLES = [
    "Senior Data Engineer", "Data Engineer", "Data Analyst", "Data Scientist",
    "Machine Learning Engineer", "Backend Developer", "Node.js Developer",
    ".NET Developer", "Laravel Developer", "React Developer", "Angular Developer",
    "Full Stack Developer", "Flutter Developer", "Android Developer",
    "DevOps Engineer", "Cloud Engineer", "QA Automation Engineer", "QA Tester",
    "Cybersecurity Analyst", "Database Administrator", "UI/UX Designer",
    "IT Support Specialist", "Network Engineer", "Project Manager",
    "Scrum Master", "Java Developer", "Golang Developer", "BI Analyst",
    "Site Reliability Engineer", "Junior Frontend Developer",
]
COMPANIES = [f"Company {i:02d}" for i in range(40)]
CITIES = [
    ("Nasr City", "Cairo"), ("Maadi", "Cairo"), ("New Cairo", "Cairo"),
    ("Heliopolis", "Cairo"), ("6th of October", "Giza"), ("Dokki", "Giza"),
    ("Mohandessin", "Giza"), ("Sheikh Zayed", "Giza"), ("Smouha", "Alexandria"),
    ("Alexandria", "Alexandria"), ("Mansoura", "Dakahlia"), ("Tanta", "Gharbia"),
    ("Unknown", "Egypt"),
]
SKILL_POOL = ["Python", "SQL", "Airflow", "dbt", "Spark", "Java", "Spring",
              "React", "TypeScript", "Docker", "Kubernetes", "AWS", "PostgreSQL",
              "Power BI", "Excel", "Node.js", ".NET", "C#", "Laravel", "PHP"]
WORK_MODES = ["on-site", "on-site", "on-site", "hybrid", "remote"]
EMP_TYPES = ["full-time", "full-time", "full-time", "part-time", "contract", "internship"]

FIELDS = [
    "job_id", "job_hash", "title_raw", "title_clean", "company_raw",
    "company_clean", "location_raw", "location_city", "location_gov",
    "salary_min", "salary_max", "salary_currency", "experience_years_min",
    "experience_years_max", "skills", "work_mode", "employment_type",
    "source", "job_url", "scraped_at", "posted_at", "run_id", "is_remote",
]

_passed = _failed = 0


def check(label, cond, detail=""):
    global _passed, _failed
    print(f"  {'✅' if cond else '❌'} {label}" + (f"  ({detail})" if detail else ""))
    if cond:
        _passed += 1
    else:
        _failed += 1


def job_hash(title, company, city):
    return hashlib.md5(f"{title.lower()}|{company.lower()}|{city.lower()}".encode()).hexdigest()


def generate(rows):
    """Write `rows` Silver records spread across sources/dates. Returns the
    set of distinct job_hash values (ground-truth unique postings)."""
    shutil.rmtree(config.silver_dir(), ignore_errors=True)
    today = date.today()
    buckets = {}  # (source, day) -> list[row]
    hashes = set()
    for i in range(rows):
        title = random.choice(TITLES)
        company = random.choice(COMPANIES)
        city, gov = random.choice(CITIES)
        src = random.choice(SOURCES)
        day = today - timedelta(days=random.randint(0, 60))
        wm = random.choice(WORK_MODES)
        has_sal = random.random() < 0.6
        smin = random.choice([8000, 12000, 18000, 25000, 35000]) if has_sal else ""
        smax = (smin + random.choice([4000, 8000, 15000])) if has_sal else ""
        n_sk = random.randint(0, 4)
        skills = "|".join(random.sample(SKILL_POOL, n_sk)) if n_sk else ""
        h = job_hash(title, company, city)
        hashes.add(h)
        row = {
            "job_id": f"{src}-{i}", "job_hash": h,
            "title_raw": title, "title_clean": title,
            "company_raw": company, "company_clean": company,
            "location_raw": f"{city}, {gov}", "location_city": city, "location_gov": gov,
            "salary_min": smin, "salary_max": smax,
            "salary_currency": "EGP" if has_sal else "",
            "experience_years_min": random.choice(["", 0, 1, 2, 3, 5]),
            "experience_years_max": "", "skills": skills,
            "work_mode": wm, "employment_type": random.choice(EMP_TYPES),
            "source": src, "job_url": f"https://{src}.example.com/job/{i}",
            "scraped_at": today.isoformat() + "T10:00:00", "posted_at": day.isoformat(),
            "run_id": f"{src}-stress", "is_remote": wm == "remote",
        }
        buckets.setdefault((src, day.isoformat()), []).append(row)

    n_files = 0
    for (src, day_iso), recs in buckets.items():
        d = os.path.join(config.silver_dir(), src, day_iso)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{src}_{day_iso}.csv"), "w", newline="",
                  encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(recs)
        n_files += 1
    return hashes, n_files


def scalar(cur, sql):
    cur.execute(sql)
    return cur.fetchone()[0]


def run_dbt():
    dbt_bin = os.path.join(ROOT, ".venv", "bin", "dbt")
    if not os.path.exists(dbt_bin):
        dbt_bin = shutil.which("dbt")
    if not dbt_bin:
        return None, "dbt binary not found"
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = DBT_DIR
    t0 = time.time()
    proc = subprocess.run([dbt_bin, "build"], cwd=DBT_DIR, env=env,
                          capture_output=True, text=True)
    return (proc, time.time() - t0)


def _run():
    print(f"=== STRESS TEST — generating {ROWS:,} postings ===")
    t0 = time.time()
    truth, n_files = generate(ROWS)
    print(f"Generated {ROWS:,} rows -> {len(truth):,} unique "
          f"({ROWS - len(truth):,} duplicates) across {n_files} files "
          f"in {time.time()-t0:.1f}s\n")

    # --- clean rebuild + timed load ---
    conn = psycopg2.connect(**config.psycopg2_dsn())
    conn.autocommit = True
    with conn.cursor() as cur:
        for t in ["bridge_job_skill", "fact_job_postings", "dim_date", "dim_source",
                  "dim_location", "dim_company", "dim_job_category", "dim_skill",
                  "ref_governorate", "etl_load_log"]:
            cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    conn.close()

    loader = WarehouseLoader()
    loader.init_schema()
    t0 = time.time()
    loader.run()
    load_secs = time.time() - t0
    loader.close()
    print(f"\n⏱  Loaded in {load_secs:.1f}s  "
          f"({len(truth)/load_secs:,.0f} postings/sec)\n")

    conn = psycopg2.connect(**config.psycopg2_dsn())
    cur = conn.cursor()

    print("--- Correctness at scale ---")
    fact_n = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    check("fact rows == unique job_hash", fact_n == len(truth),
          f"fact={fact_n:,}, unique={len(truth):,}")
    check("no duplicate job_hash",
          scalar(cur, "SELECT count(DISTINCT job_hash) FROM fact_job_postings") == fact_n)
    orphans = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f
        LEFT JOIN dim_company c ON f.company_key=c.company_key
        LEFT JOIN dim_location l ON f.location_key=l.location_key
        LEFT JOIN dim_job_category k ON f.category_key=k.category_key
        LEFT JOIN dim_source s ON f.source_key=s.source_key
        WHERE c.company_key IS NULL OR l.location_key IS NULL
           OR k.category_key IS NULL OR s.source_key IS NULL""")
    check("no orphan foreign keys", orphans == 0, f"orphans={orphans}")
    check("all rows have valid work_mode",
          scalar(cur, "SELECT count(*) FROM fact_job_postings "
                      "WHERE work_mode IN ('remote','hybrid','on-site')") == fact_n)
    check("skills bridged at scale",
          scalar(cur, "SELECT count(*) FROM bridge_job_skill") > 0)

    print("\n--- Idempotency under volume ---")
    loader = WarehouseLoader()
    t0 = time.time()
    loader.run(reload=True)
    reload_secs = time.time() - t0
    loader.close()
    n_after = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    check("forced reload adds no rows", n_after == fact_n, f"{fact_n:,} -> {n_after:,}")
    print(f"    (reload took {reload_secs:.1f}s)")

    print("\n--- dbt build on the large dataset ---")
    result = run_dbt()
    if result[0] is None:
        check("dbt available", False, result[1])
    else:
        proc, dbt_secs = result
        ok = proc.returncode == 0
        check("dbt build succeeded", ok, f"rc={proc.returncode}, {dbt_secs:.1f}s")
        if not ok:
            print(proc.stdout[-3000:])
            print(proc.stderr[-2000:])
        else:
            # tail of dbt summary
            for line in proc.stdout.strip().splitlines()[-4:]:
                print("    " + line)
            for mart, schema in [("mart_in_demand_roles", "marts"),
                                 ("mart_skill_demand", "marts"),
                                 ("mart_salary_intelligence", "marts"),
                                 ("mart_company_insights", "marts")]:
                n = scalar(cur, f"SELECT count(*) FROM {schema}.{mart}")
                check(f"{mart} populated", n > 0, f"rows={n}")

    cur.close()
    conn.close()

    print(f"\n{'='*52}")
    print(f"  STRESS RESULT: {_passed} passed, {_failed} failed "
          f"| {len(truth):,} postings @ {len(truth)/load_secs:,.0f}/s")
    print(f"{'='*52}")


def main():
    # Isolated temp workspace + throwaway DB (dbt subprocess inherits
    # PGDATABASE), so the high-volume run never touches real data.
    with isolated_workspace("stress"):
        _run()
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
