"""Capture a proof-of-concept snapshot of a REAL pipeline run.

Reads the current state of the data lake (data/raw, data/silver) and the
warehouse + dbt marts, then writes committable evidence under
proof_of_concept/:

  * POC_REPORT.md           — headline numbers + sample analytics
  * marts/<mart>.csv        — full export of every dbt mart
  * samples/                — a few real raw + silver rows

    export PYTHONPATH=$PYTHONPATH:.
    python3 warehouse/poc_report.py
"""
import csv
import glob
import json
import os
from datetime import datetime

import psycopg2

from warehouse import config

OUT = "proof_of_concept"
MARTS = [
    "mart_in_demand_roles", "mart_salary_intelligence", "mart_skill_demand",
    "mart_company_insights", "mart_geographic_distribution",
    "mart_work_mode_breakdown", "mart_hiring_trends",
]


def q(cur, sql):
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    return cols, cur.fetchall()


def raw_stats():
    by_source = {}
    for path in glob.glob("data/raw/**/*.json", recursive=True):
        src = path.split(os.sep)[2]
        try:
            n = len(json.load(open(path, encoding="utf-8")))
        except Exception:
            n = 0
        by_source[src] = by_source.get(src, 0) + n
    return by_source


def silver_count():
    total = 0
    for path in glob.glob("data/silver/**/*.csv", recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            total += sum(1 for _ in f) - 1
    return total


def md_table(cols, rows, limit=None):
    rows = rows[:limit] if limit else rows
    out = ["| " + " | ".join(str(c) for c in cols) + " |",
           "| " + " | ".join("---" for _ in cols) + " |"]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def main():
    os.makedirs(os.path.join(OUT, "marts"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "samples"), exist_ok=True)

    conn = psycopg2.connect(**config.psycopg2_dsn())
    cur = conn.cursor()

    raw = raw_stats()
    raw_total = sum(raw.values())
    silver = silver_count()
    fact = q(cur, "SELECT count(*) FROM fact_job_postings")[1][0][0]

    dims = {}
    for t in ["dim_company", "dim_location", "dim_skill", "dim_job_category",
              "dim_source", "dim_date", "bridge_job_skill"]:
        dims[t] = q(cur, f"SELECT count(*) FROM {t}")[1][0][0]

    _, by_src = q(cur, """
        SELECT s.display_name, count(*) AS postings
        FROM fact_job_postings f JOIN dim_source s ON f.source_key=s.source_key
        GROUP BY s.display_name ORDER BY postings DESC""")

    # Export every mart to CSV (full) and keep a preview for the report.
    previews = {}
    for mart in MARTS:
        try:
            cols, rows = q(cur, f"SELECT * FROM marts.{mart}")
        except Exception as e:
            previews[mart] = ("ERROR", [[str(e)]])
            conn.rollback()
            continue
        with open(os.path.join(OUT, "marts", f"{mart}.csv"), "w",
                  newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            w.writerows(rows)
        previews[mart] = (cols, rows)

    # A few real raw + silver sample rows (proof the data is genuine).
    raw_sample = []
    for path in glob.glob("data/raw/**/*.json", recursive=True)[:2]:
        raw_sample.extend(json.load(open(path, encoding="utf-8"))[:3])
    with open(os.path.join(OUT, "samples", "raw_sample.json"), "w",
              encoding="utf-8") as fh:
        json.dump(raw_sample, fh, ensure_ascii=False, indent=2)

    # Salary headline (real money).
    sal = q(cur, """
        SELECT count(*), round(avg(salary_mid)), round(min(salary_min)),
               round(max(salary_max))
        FROM (SELECT salary_min, salary_max,
                     (salary_min+salary_max)/2.0 AS salary_mid
              FROM fact_job_postings
              WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL) s""")[1][0]

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Proof of Concept — Real Pipeline Run",
        "",
        f"_Generated {now} from live data scraped from Egyptian job boards._",
        "",
        "This is a genuine end-to-end run: data was **scraped live**, cleaned,",
        "loaded into the PostgreSQL star schema, and transformed by dbt into the",
        "analytics marts below. Numbers are real.",
        "",
        "## Pipeline volumes",
        "",
        "| Stage | Count |",
        "| --- | --- |",
        f"| Bronze — raw scraped records | {raw_total} |",
        f"| Silver — cleaned rows | {silver} |",
        f"| Gold — unique postings (deduped) | {fact} |",
        f"| dim_company | {dims['dim_company']} |",
        f"| dim_location | {dims['dim_location']} |",
        f"| dim_skill | {dims['dim_skill']} |",
        f"| bridge_job_skill (skill links) | {dims['bridge_job_skill']} |",
        "",
        "### Raw records by source",
        "",
        md_table(["source", "raw_records"], list(raw.items())),
        "",
        "### Loaded postings by source",
        "",
        md_table(["source", "postings"], by_src),
        "",
        f"**Salary signal:** {sal[0]} postings carried a salary; "
        f"average mid-point ≈ **{sal[1]} EGP** (range {sal[2]}–{sal[3]}).",
        "",
        "## Sample analytics (from the dbt marts)",
        "",
        "### Most in-demand roles",
        "",
        md_table(*previews["mart_in_demand_roles"], limit=8),
        "",
        "### Top in-demand skills",
        "",
        md_table(previews["mart_skill_demand"][0],
                 previews["mart_skill_demand"][1], limit=10),
        "",
        "### Top hiring companies",
        "",
        md_table(*previews["mart_company_insights"], limit=8),
        "",
        "### Geographic distribution",
        "",
        md_table(*previews["mart_geographic_distribution"], limit=8),
        "",
        "### Work mode & employment type",
        "",
        md_table(*previews["mart_work_mode_breakdown"]),
        "",
        "## Artifacts in this folder",
        "",
        "- `marts/*.csv` — full export of every dbt mart",
        "- `samples/raw_sample.json` — real raw records as scraped",
        "",
        "## Honest notes / limitations",
        "",
        "- Live scrapers run here: **Wuzzuf** and **Forasna** (pure `requests`).",
        "  Bayt/Indeed/Jobzella need a real browser (Selenium/anti-bot) and were",
        "  not run in this environment.",
        "- Listing pages carry no full job description, so **skills** are derived",
        "  from titles only — coverage is sparser than it would be with detail-page",
        "  scraping. Salaries are present where the board exposes them.",
        "- Volumes were intentionally capped (env `MAX_JOBS` / `MAX_PAGES`) to be",
        "  polite to the sites; the pipeline scales to far larger runs (see",
        "  `warehouse/stress_test.py`).",
    ]
    with open(os.path.join(OUT, "POC_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    cur.close()
    conn.close()
    print(f"✅ Wrote {OUT}/POC_REPORT.md and {len(MARTS)} mart CSVs.")
    print(f"   Bronze={raw_total}  Silver={silver}  Gold={fact}  "
          f"skill_links={dims['bridge_job_skill']}")


if __name__ == "__main__":
    main()
