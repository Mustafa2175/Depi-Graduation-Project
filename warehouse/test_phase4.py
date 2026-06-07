"""End-to-end test for Phase 4 (PostgreSQL star schema + loader).

Runs a full, clean cycle against the configured PostgreSQL database:

    1.  ensure sample Silver data exists
    2.  drop & rebuild the warehouse (schema + seed)
    3.  load all Silver CSVs
    4.  assert structural & business invariants
    5.  assert idempotency  (a reload changes no fact counts, adds no rows)
    6.  print sample analytics (the questions Phase 7 will formalise)

Exit code 0 = all checks passed.

    export PYTHONPATH=$PYTHONPATH:.
    python3 warehouse/test_phase4.py
"""
import glob
import os
import sys

import psycopg2

from warehouse import config
from warehouse.isolation import isolated_workspace
from warehouse.load_to_postgres import WarehouseLoader

PHASE4_TABLES = [
    "bridge_job_skill", "fact_job_postings", "dim_date", "dim_source",
    "dim_location", "dim_company", "dim_job_category", "dim_skill",
    "ref_governorate", "etl_load_log",
]

_passed = 0
_failed = 0


def check(label, condition, detail=""):
    global _passed, _failed
    mark = "✅" if condition else "❌"
    print(f"  {mark} {label}" + (f"  ({detail})" if detail else ""))
    if condition:
        _passed += 1
    else:
        _failed += 1


def scalar(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchone()[0]


def expected_unique_hashes():
    """Distinct job_hash count across all Silver CSVs (ground truth)."""
    import csv
    hashes = set()
    for path in glob.glob(os.path.join(config.silver_dir(), "**", "*.csv"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                h = (row.get("job_hash") or "").strip()
                if h:
                    hashes.add(h)
    return hashes


def drop_warehouse(cur):
    for t in PHASE4_TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")


def _run():
    # 1. (re)generate the controlled sample Silver this test relies on
    #    (independent of any real pipeline output already in data/silver).
    import shutil
    shutil.rmtree(config.silver_dir(), ignore_errors=True)
    from warehouse import make_sample_data
    make_sample_data.main()

    truth = expected_unique_hashes()
    print(f"\nGround truth: {len(truth)} unique job_hash values across Silver CSVs.\n")

    # 2. clean rebuild
    conn = psycopg2.connect(**config.psycopg2_dsn())
    conn.autocommit = True
    with conn.cursor() as cur:
        drop_warehouse(cur)
    conn.close()
    print("Dropped any existing warehouse tables. Rebuilding + loading...\n")

    # 3. load
    loader = WarehouseLoader()
    loader.init_schema()
    loader.run()
    loader.close()

    # 4 & 5. assertions
    conn = psycopg2.connect(**config.psycopg2_dsn())
    cur = conn.cursor()

    print("\n--- Structural & business invariants ---")
    fact_n = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    check("fact row count == unique job_hash count",
          fact_n == len(truth), f"fact={fact_n}, truth={len(truth)}")

    distinct_hashes = scalar(cur, "SELECT count(DISTINCT job_hash) FROM fact_job_postings")
    check("job_hash is unique in fact (no duplicates)",
          distinct_hashes == fact_n, f"distinct={distinct_hashes}")

    # Cross-source duplicate collapsed to exactly one fact row.
    dup_rows = scalar(cur,
        "SELECT count(*) FROM fact_job_postings f JOIN dim_company c "
        "ON f.company_key=c.company_key WHERE c.company_clean='Fawry' "
        "AND f.title_clean='Senior Python Data Engineer'")
    check("cross-source duplicate collapsed to 1 row", dup_rows == 1, f"rows={dup_rows}")

    # Referential integrity — no orphan FKs.
    orphans = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f
        LEFT JOIN dim_source   s ON f.source_key   = s.source_key
        LEFT JOIN dim_company  c ON f.company_key  = c.company_key
        LEFT JOIN dim_location l ON f.location_key = l.location_key
        LEFT JOIN dim_job_category k ON f.category_key = k.category_key
        WHERE s.source_key IS NULL OR c.company_key IS NULL
           OR l.location_key IS NULL OR k.category_key IS NULL
    """)
    check("no orphan foreign keys in fact", orphans == 0, f"orphans={orphans}")

    null_keys = scalar(cur, """
        SELECT count(*) FROM fact_job_postings
        WHERE source_key IS NULL OR company_key IS NULL
           OR location_key IS NULL OR category_key IS NULL
    """)
    check("all fact dimension keys are NOT NULL", null_keys == 0, f"nulls={null_keys}")

    # Every location's governorate exists in the reference table.
    bad_gov = scalar(cur, """
        SELECT count(*) FROM dim_location l
        LEFT JOIN ref_governorate g ON l.location_gov = g.governorate
        WHERE g.governorate IS NULL
    """)
    check("every location_gov is a known governorate", bad_gov == 0, f"unknown={bad_gov}")

    # SCD Type 2 on dim_company: exactly one current row per company name,
    # and the changed company ("Fawry") kept history.
    multi_current = scalar(cur, """
        SELECT count(*) FROM (
            SELECT company_clean FROM dim_company WHERE is_current
            GROUP BY company_clean HAVING count(*) > 1
        ) x
    """)
    check("exactly one current row per company (SCD2)", multi_current == 0,
          f"violations={multi_current}")

    fawry_versions = scalar(cur,
        "SELECT count(*) FROM dim_company WHERE company_clean='Fawry'")
    fawry_hist = scalar(cur,
        "SELECT count(*) FROM dim_company WHERE company_clean='Fawry' AND NOT is_current")
    check("SCD2 captured Fawry history (>1 version, has non-current)",
          fawry_versions > 1 and fawry_hist >= 1,
          f"versions={fawry_versions}, historical={fawry_hist}")

    # Categorisation actually assigned non-Other categories.
    categorized = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f JOIN dim_job_category k
        ON f.category_key=k.category_key WHERE k.category_name <> 'Other'
    """)
    check("titles were categorised (not all 'Other')", categorized > 0,
          f"non-Other={categorized}/{fact_n}")

    skill_links = scalar(cur, "SELECT count(*) FROM bridge_job_skill")
    check("skills detected and bridged", skill_links > 0, f"links={skill_links}")

    # Skills must come from the Silver `skills` column, not be re-derived from
    # the title. "Senior Python Data Engineer" has no 'Airflow'/'dbt' in its
    # title, so finding them linked proves the column-sourced path is used.
    airflow_linked = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f
        JOIN bridge_job_skill b ON f.job_key=b.job_key
        JOIN dim_skill s ON b.skill_key=s.skill_key
        WHERE f.title_clean='Senior Python Data Engineer'
          AND s.skill_name IN ('Airflow','dbt','Spark')
    """)
    check("skills sourced from Silver column (Airflow/dbt/Spark linked)",
          airflow_linked >= 1, f"matches={airflow_linked}")

    # work_mode / employment_type populated and within the allowed vocabularies.
    wm_ok = scalar(cur, """
        SELECT count(*) FROM fact_job_postings
        WHERE work_mode IN ('remote','hybrid','on-site')
    """)
    check("all rows have a valid work_mode", wm_ok == fact_n, f"valid={wm_ok}/{fact_n}")

    et_ok = scalar(cur, """
        SELECT count(*) FROM fact_job_postings
        WHERE employment_type IN
            ('full-time','part-time','contract','internship','freelance')
    """)
    check("all rows have a valid employment_type", et_ok == fact_n,
          f"valid={et_ok}/{fact_n}")

    # Date dimension populated and consistent.
    bad_dates = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f
        LEFT JOIN dim_date d ON f.posted_date_key = d.date_key
        WHERE f.posted_date_key IS NOT NULL AND d.date_key IS NULL
    """)
    check("all posted_date_keys resolve in dim_date", bad_dates == 0, f"bad={bad_dates}")

    print("\n--- Idempotency ---")
    # Re-run incremental: nothing new (all files already in load log).
    loader = WarehouseLoader()
    loader.run()
    loader.close()
    n_after_inc = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    check("incremental re-run adds no rows", n_after_inc == fact_n,
          f"{fact_n} -> {n_after_inc}")

    # Force reload of every file: still no new rows (upsert on job_hash).
    loader = WarehouseLoader()
    loader.run(reload=True)
    loader.close()
    n_after_reload = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    bridge_after = scalar(cur, "SELECT count(*) FROM bridge_job_skill")
    check("forced reload adds no fact rows", n_after_reload == fact_n,
          f"{fact_n} -> {n_after_reload}")
    check("forced reload keeps bridge stable", bridge_after == skill_links,
          f"{skill_links} -> {bridge_after}")

    # 6. sample analytics
    print("\n--- Sample analytics (preview of Phase 7) ---")
    cur.execute("""
        SELECT k.category_name, count(*) AS postings
        FROM fact_job_postings f JOIN dim_job_category k ON f.category_key=k.category_key
        GROUP BY k.category_name ORDER BY postings DESC LIMIT 5
    """)
    print("  Top categories by demand:")
    for name, n in cur.fetchall():
        print(f"    {name:<28} {n}")

    cur.execute("""
        SELECT l.location_gov, count(*) AS postings
        FROM fact_job_postings f JOIN dim_location l ON f.location_key=l.location_key
        GROUP BY l.location_gov ORDER BY postings DESC LIMIT 5
    """)
    print("  Postings by governorate:")
    for gov, n in cur.fetchall():
        print(f"    {gov:<28} {n}")

    cur.execute("""
        SELECT round(avg((salary_min+salary_max)/2)) AS avg_mid
        FROM fact_job_postings WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL
    """)
    print(f"  Avg mid-point salary (where known): {cur.fetchone()[0]}")

    cur.execute("""
        SELECT s.skill_name, count(*) AS c
        FROM bridge_job_skill b JOIN dim_skill s ON b.skill_key=s.skill_key
        GROUP BY s.skill_name ORDER BY c DESC LIMIT 5
    """)
    print("  Top in-demand skills:")
    for name, n in cur.fetchall():
        print(f"    {name:<28} {n}")

    cur.execute("""
        SELECT work_mode, count(*) FROM fact_job_postings
        GROUP BY work_mode ORDER BY count(*) DESC
    """)
    print("  Work mode breakdown:")
    for mode, n in cur.fetchall():
        print(f"    {mode:<28} {n}")

    cur.execute("""
        SELECT employment_type, count(*) FROM fact_job_postings
        GROUP BY employment_type ORDER BY count(*) DESC
    """)
    print("  Employment type breakdown:")
    for et, n in cur.fetchall():
        print(f"    {et:<28} {n}")

    cur.close()
    conn.close()


def main():
    # Run the whole suite against an isolated temp workspace + throwaway DB so
    # it never touches real data/ or the real warehouse.
    with isolated_workspace("phase4"):
        _run()
    print(f"\n{'='*48}")
    print(f"  RESULT: {_passed} passed, {_failed} failed")
    print(f"{'='*48}")
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
