"""Full pipeline end-to-end test: Bronze -> Silver -> Gold.

Unlike test_phase4.py (which feeds the warehouse crafted Silver to exercise
specific scenarios), this test runs the **real** cleaning pipeline
(processing/main.py) on generated raw JSON, then loads the resulting Silver
into the star schema. It proves the closed Phase 3 gaps actually work:

  * skills are extracted from job *descriptions* by the cleaning layer
  * work_mode / employment_type are classified
  * the quality gate quarantines invalid records
  * the warehouse consumes the real Silver `skills` column end-to-end

    export PYTHONPATH=$PYTHONPATH:.
    python3 warehouse/test_pipeline.py
"""
import csv
import glob
import os
import sys

import psycopg2

from warehouse import config, make_raw_data
from warehouse.isolation import isolated_workspace
from warehouse.load_to_postgres import WarehouseLoader
from warehouse.test_phase4 import check, scalar, drop_warehouse
import warehouse.test_phase4 as t4


def read_silver_rows():
    rows = []
    for path in glob.glob(os.path.join(config.silver_dir(), "**", "*.csv"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(csv.DictReader(f))
    return rows


def _run():
    # 1. generate raw + 2. run the REAL cleaning pipeline (writes into the
    #    isolated workspace dirs configured by isolated_workspace()).
    make_raw_data.main()
    print()
    from processing.main import run_pipeline
    run_pipeline()

    print("\n--- Phase 3 (cleaning layer) invariants ---")
    silver = read_silver_rows()
    check("Silver layer produced rows", len(silver) > 0, f"rows={len(silver)}")

    cols = set(silver[0].keys()) if silver else set()
    for col in ("skills", "work_mode", "employment_type"):
        check(f"Silver has '{col}' column", col in cols)

    with_skills = [r for r in silver if r.get("skills", "").strip()]
    check("skills extracted for most postings",
          len(with_skills) >= 0.6 * len(silver),
          f"{len(with_skills)}/{len(silver)}")

    # Skills must be read from the DESCRIPTION, not the title.
    de = [r for r in silver
          if r.get("title_clean") == "Senior Data Engineer"
          and r.get("company_clean") == "Fawry"]
    de_has_airflow = any("Airflow" in r.get("skills", "") for r in de)
    check("skills pulled from description (Airflow on Data Engineer role)",
          de_has_airflow, f"matching rows={len(de)}")

    modes = {r.get("work_mode") for r in silver}
    check("work_mode classified (multiple values seen)",
          modes.issubset({"remote", "hybrid", "on-site"}) and len(modes) >= 2,
          f"modes={sorted(modes)}")

    etypes = {r.get("employment_type") for r in silver}
    check("employment_type classified",
          etypes.issubset({"full-time", "part-time", "contract",
                           "internship", "freelance"}) and len(etypes) >= 2,
          f"types={sorted(etypes)}")

    # Quality gate quarantined the two bad raw records.
    failed_root = os.getenv("FAILED_DIR", "data/failed")
    failed_rows = sum(
        sum(1 for _ in csv.DictReader(open(p, encoding="utf-8-sig")))
        for p in glob.glob(os.path.join(failed_root, "**", "*.csv"), recursive=True))
    check("quality gate quarantined invalid records", failed_rows >= 2,
          f"quarantined={failed_rows}")
    bad_in_silver = [r for r in silver if not r.get("title_clean", "").strip()
                     or not r.get("job_url", "").startswith("http")]
    check("no invalid rows leaked into Silver", len(bad_in_silver) == 0,
          f"leaked={len(bad_in_silver)}")

    # 4. load real Silver into the warehouse
    print("\nRebuilding warehouse and loading the REAL Silver output...\n")
    conn = psycopg2.connect(**config.psycopg2_dsn())
    conn.autocommit = True
    with conn.cursor() as cur:
        drop_warehouse(cur)
    conn.close()

    loader = WarehouseLoader()
    loader.init_schema()
    loader.run()
    loader.close()

    print("\n--- Phase 4 (warehouse) invariants on real data ---")
    conn = psycopg2.connect(**config.psycopg2_dsn())
    cur = conn.cursor()

    unique_hashes = {r["job_hash"] for r in silver if r.get("job_hash", "").strip()}
    fact_n = scalar(cur, "SELECT count(*) FROM fact_job_postings")
    check("fact rows == unique job_hash in Silver",
          fact_n == len(unique_hashes), f"fact={fact_n}, unique={len(unique_hashes)}")

    dup_rows = scalar(cur,
        "SELECT count(*) FROM fact_job_postings f JOIN dim_company c "
        "ON f.company_key=c.company_key WHERE c.company_clean='Fawry' "
        "AND f.title_clean='Senior Data Engineer'")
    check("cross-source duplicate collapsed to 1 row", dup_rows == 1, f"rows={dup_rows}")

    airflow_linked = scalar(cur, """
        SELECT count(*) FROM fact_job_postings f
        JOIN bridge_job_skill b ON f.job_key=b.job_key
        JOIN dim_skill s ON b.skill_key=s.skill_key
        WHERE f.title_clean='Senior Data Engineer' AND s.skill_name='Airflow'
    """)
    check("description-derived skill (Airflow) reached the warehouse",
          airflow_linked >= 1, f"links={airflow_linked}")

    wm_ok = scalar(cur,
        "SELECT count(*) FROM fact_job_postings WHERE work_mode IS NOT NULL")
    check("work_mode populated in fact", wm_ok == fact_n, f"{wm_ok}/{fact_n}")
    et_ok = scalar(cur,
        "SELECT count(*) FROM fact_job_postings WHERE employment_type IS NOT NULL")
    check("employment_type populated in fact", et_ok == fact_n, f"{et_ok}/{fact_n}")

    print("\n--- Sample analytics on real pipeline output ---")
    cur.execute("""
        SELECT s.skill_name, count(*) c FROM bridge_job_skill b
        JOIN dim_skill s ON b.skill_key=s.skill_key
        GROUP BY s.skill_name ORDER BY c DESC LIMIT 6
    """)
    print("  Top skills:", ", ".join(f"{n}({c})" for n, c in cur.fetchall()))
    cur.execute("SELECT work_mode, count(*) FROM fact_job_postings GROUP BY work_mode ORDER BY 2 DESC")
    print("  Work mode:", ", ".join(f"{m}={c}" for m, c in cur.fetchall()))
    cur.execute("SELECT employment_type, count(*) FROM fact_job_postings GROUP BY employment_type ORDER BY 2 DESC")
    print("  Employment:", ", ".join(f"{e}={c}" for e, c in cur.fetchall()))

    cur.close()
    conn.close()


def main():
    # Isolated temp workspace + throwaway DB: never touches real data/ or the
    # real warehouse.
    with isolated_workspace("pipeline"):
        _run()
    print(f"\n{'='*48}")
    print(f"  RESULT: {t4._passed} passed, {t4._failed} failed")
    print(f"{'='*48}")
    sys.exit(1 if t4._failed else 0)


if __name__ == "__main__":
    main()
