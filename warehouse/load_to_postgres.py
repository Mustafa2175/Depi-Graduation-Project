"""Phase 4 loader: Silver (cleaned CSV)  ->  PostgreSQL star schema (Gold).

Responsibilities
----------------
* (optionally) build the schema and seed reference data
* discover Silver CSVs under data/silver/**, skipping ones already loaded
* resolve / create dimension keys (date, source, location, company-SCD2,
  category, skill)
* idempotently upsert the fact table keyed on job_hash (re-running never
  duplicates rows)
* link detected skills via the bridge table
* record every processed file in etl_load_log for incremental runs

Usage
-----
    export PYTHONPATH=$PYTHONPATH:.
    python3 warehouse/load_to_postgres.py --init        # create schema + seed, then load
    python3 warehouse/load_to_postgres.py               # incremental load of new files
    python3 warehouse/load_to_postgres.py --reload      # reprocess every file
"""
from __future__ import annotations

import argparse
import glob
import os
import re
from datetime import date, datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from warehouse import config

SQL_DIR = os.path.join(os.path.dirname(__file__), "sql")

SILVER_COLUMNS = [
    "job_id", "job_hash", "title_raw", "title_clean", "company_raw",
    "company_clean", "location_raw", "location_city", "location_gov",
    "salary_min", "salary_max", "salary_currency", "experience_years_min",
    "experience_years_max", "source", "job_url", "scraped_at", "posted_at",
    "run_id", "is_remote",
]


# ----------------------------------------------------------------------
# Small value-coercion helpers (Silver CSVs are all text)
# ----------------------------------------------------------------------
def _to_num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(v):
    n = _to_num(v)
    return int(n) if n is not None else None


def _to_bool(v):
    return str(v).strip().lower() in ("true", "1", "yes", "t")


def _clean_str(v, default=""):
    if v is None:
        return default
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return default
    return s


def _date_key(date_str):
    """'2026-06-07' (or ISO datetime) -> (20260607, date) ; (None, None) on failure."""
    s = _clean_str(date_str)
    if not s:
        return None, None
    s = s[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None, None
    return d.year * 10000 + d.month * 100 + d.day, d


# ----------------------------------------------------------------------
class WarehouseLoader:
    def __init__(self):
        self.conn = psycopg2.connect(**config.psycopg2_dsn())
        self.conn.autocommit = False
        self.cur = self.conn.cursor()
        # in-memory caches, primed lazily
        self._sources = {}
        self._locations = {}
        self._companies = {}        # company_clean -> (company_key, company_raw)
        self._categories = []       # [(key, name, [keywords])]
        self._skills = []           # [(key, name, compiled_regex)]
        self._dates = set()
        self._govs = set()

    # -- schema / seed -------------------------------------------------
    def init_schema(self):
        for fname in ("01_schema.sql", "02_seed.sql"):
            with open(os.path.join(SQL_DIR, fname), "r", encoding="utf-8") as f:
                self.cur.execute(f.read())
        self.conn.commit()
        print("✅ Schema created and reference data seeded.")

    # -- cache priming -------------------------------------------------
    def _prime_caches(self):
        self.cur.execute("SELECT source_name, source_key FROM dim_source")
        self._sources = dict(self.cur.fetchall())

        self.cur.execute("SELECT location_city, location_gov, location_key FROM dim_location")
        self._locations = {(c, g): k for c, g, k in self.cur.fetchall()}

        self.cur.execute(
            "SELECT company_clean, company_key, company_raw FROM dim_company WHERE is_current"
        )
        self._companies = {name: (key, raw) for name, key, raw in self.cur.fetchall()}

        self.cur.execute("SELECT category_key, category_name, keywords FROM dim_job_category")
        self._categories = [(k, n, [kw.lower() for kw in (kws or [])])
                            for k, n, kws in self.cur.fetchall()]

        self.cur.execute("SELECT skill_key, skill_name FROM dim_skill")
        self._skills = []                # regex list — fallback title detection
        self._skill_by_name = {}         # name.lower() -> skill_key
        for key, name in self.cur.fetchall():
            self._skill_by_name[name.lower()] = key
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])")
            self._skills.append((key, name, pat))

        self.cur.execute("SELECT date_key FROM dim_date")
        self._dates = {r[0] for r in self.cur.fetchall()}

        self.cur.execute("SELECT governorate FROM ref_governorate")
        self._govs = {r[0] for r in self.cur.fetchall()}

    # -- dimension resolvers ------------------------------------------
    def _get_source_key(self, name):
        name = (name or "unknown").lower().strip()
        if name not in self._sources:
            self.cur.execute(
                "INSERT INTO dim_source (source_name) VALUES (%s) "
                "ON CONFLICT (source_name) DO UPDATE SET source_name = EXCLUDED.source_name "
                "RETURNING source_key", (name,))
            self._sources[name] = self.cur.fetchone()[0]
        return self._sources[name]

    def _ensure_gov(self, gov):
        if gov not in self._govs:
            self.cur.execute(
                "INSERT INTO ref_governorate (governorate, region) VALUES (%s, 'Unknown') "
                "ON CONFLICT (governorate) DO NOTHING", (gov,))
            self._govs.add(gov)

    def _get_location_key(self, city, gov):
        city = _clean_str(city, "Unknown")
        gov = _clean_str(gov, "Egypt")
        if (city, gov) not in self._locations:
            self._ensure_gov(gov)
            self.cur.execute(
                "INSERT INTO dim_location (location_city, location_gov) VALUES (%s, %s) "
                "ON CONFLICT (location_city, location_gov) DO UPDATE "
                "SET location_city = EXCLUDED.location_city RETURNING location_key",
                (city, gov))
            self._locations[(city, gov)] = self.cur.fetchone()[0]
        return self._locations[(city, gov)]

    def _get_company_key(self, company_clean, company_raw):
        """SCD Type 2: keep history when a company's attributes change."""
        company_clean = _clean_str(company_clean, "Unknown")
        company_raw = _clean_str(company_raw, company_clean)
        existing = self._companies.get(company_clean)
        if existing is None:
            self.cur.execute(
                "INSERT INTO dim_company (company_clean, company_raw) VALUES (%s, %s) "
                "RETURNING company_key", (company_clean, company_raw))
            key = self.cur.fetchone()[0]
            self._companies[company_clean] = (key, company_raw)
            return key
        key, old_raw = existing
        if old_raw != company_raw:
            # close the current row and open a new version (SCD2)
            self.cur.execute(
                "UPDATE dim_company SET is_current = FALSE, valid_to = CURRENT_DATE "
                "WHERE company_key = %s", (key,))
            self.cur.execute(
                "INSERT INTO dim_company (company_clean, company_raw) VALUES (%s, %s) "
                "RETURNING company_key", (company_clean, company_raw))
            key = self.cur.fetchone()[0]
            self._companies[company_clean] = (key, company_raw)
        return key

    def _ensure_date(self, date_key, d: date):
        if date_key is None or date_key in self._dates:
            return
        self.cur.execute(
            "INSERT INTO dim_date (date_key, full_date, year, quarter, month, "
            "month_name, day, day_of_week, day_name, week_of_year, is_weekend) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (date_key) DO NOTHING",
            (date_key, d, d.year, (d.month - 1) // 3 + 1, d.month,
             d.strftime("%B"), d.day, d.isoweekday(), d.strftime("%A"),
             int(d.strftime("%V")), d.isoweekday() in (5, 6)))
        self._dates.add(date_key)

    def _categorize(self, title_clean):
        title = (title_clean or "").lower()
        best_key, best_score = None, 0
        other_key = None
        for key, name, keywords in self._categories:
            if name == "Other":
                other_key = key
                continue
            score = sum(1 for kw in keywords if kw in title)
            if score > best_score:
                best_key, best_score = key, score
        return best_key if best_key is not None else other_key

    def _get_skill_key(self, skill_name):
        """Resolve a skill to its key, creating the dimension row if new."""
        name = skill_name.strip()
        if not name:
            return None
        key = self._skill_by_name.get(name.lower())
        if key is None:
            self.cur.execute(
                "INSERT INTO dim_skill (skill_name) VALUES (%s) "
                "ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name "
                "RETURNING skill_key", (name,))
            key = self.cur.fetchone()[0]
            self._skill_by_name[name.lower()] = key
        return key

    def _skills_from_column(self, skills_str):
        """Skills come pre-extracted from the Silver layer (pipe-delimited)."""
        keys = []
        for raw in str(skills_str or "").split("|"):
            key = self._get_skill_key(raw)
            if key is not None and key not in keys:
                keys.append(key)
        return keys

    def _detect_skills(self, title_clean):
        """Fallback when the Silver file predates the skills column."""
        title = (title_clean or "").lower()
        return [key for key, _name, pat in self._skills if pat.search(title)]

    # -- per-file load -------------------------------------------------
    def load_file(self, path, reload=False):
        if not reload:
            self.cur.execute("SELECT 1 FROM etl_load_log WHERE file_path = %s", (path,))
            if self.cur.fetchone():
                print(f"⏭️  Skipping already-loaded file: {path}")
                return 0, 0

        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        missing = [c for c in SILVER_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{path} is missing required columns: {missing}")

        # Enrichment columns are optional (older Silver files may lack them).
        has_skills = "skills" in df.columns
        has_work_mode = "work_mode" in df.columns
        has_emp_type = "employment_type" in df.columns
        has_salary_period = "salary_period" in df.columns

        # Keyed by job_hash so intra-file duplicates collapse to one row
        # (last occurrence wins) — otherwise a single INSERT ... ON CONFLICT
        # batch would try to update the same row twice and Postgres errors.
        rows_by_hash, skills_per_hash = {}, {}
        for _, r in df.iterrows():
            job_hash = _clean_str(r["job_hash"])
            if not job_hash:
                continue  # cannot dedup without a hash

            p_key, p_date = _date_key(r["posted_at"])
            s_key, s_date = _date_key(r["scraped_at"])
            self._ensure_date(p_key, p_date)
            self._ensure_date(s_key, s_date)

            title_clean = _clean_str(r["title_clean"], _clean_str(r["title_raw"]))

            rows_by_hash[job_hash] = (
                job_hash,
                _clean_str(r["job_id"]) or None,
                self._get_source_key(r["source"]),
                self._get_company_key(r["company_clean"], r["company_raw"]),
                self._get_location_key(r["location_city"], r["location_gov"]),
                self._categorize(title_clean),
                p_key, s_key,
                _clean_str(r["title_raw"]) or None,
                title_clean or None,
                _to_num(r["salary_min"]), _to_num(r["salary_max"]),
                _clean_str(r["salary_currency"]) or None,
                (_clean_str(r["salary_period"]) or None) if has_salary_period else None,
                _to_int(r["experience_years_min"]), _to_int(r["experience_years_max"]),
                _to_bool(r["is_remote"]),
                (_clean_str(r["work_mode"]) or None) if has_work_mode else None,
                (_clean_str(r["employment_type"]) or None) if has_emp_type else None,
                _clean_str(r["job_url"]) or None,
                _clean_str(r["run_id"]) or None,
            )
            # Prefer skills pre-extracted by the cleaning layer; fall back to
            # title-derived detection only for legacy files without the column.
            if has_skills:
                skills_per_hash[job_hash] = self._skills_from_column(r["skills"])
            else:
                skills_per_hash[job_hash] = self._detect_skills(title_clean)

        rows = list(rows_by_hash.values())
        if not rows:
            self._record_load(path, len(df), 0, 0)
            return 0, 0

        # Upsert fact rows; xmax = 0 marks freshly-inserted rows.
        sql = """
            INSERT INTO fact_job_postings (
                job_hash, source_job_id, source_key, company_key, location_key,
                category_key, posted_date_key, scraped_date_key, title_raw,
                title_clean, salary_min, salary_max, salary_currency, salary_period,
                experience_years_min, experience_years_max, is_remote,
                work_mode, employment_type, job_url, run_id
            ) VALUES %s
            ON CONFLICT (job_hash) DO UPDATE SET
                source_key       = EXCLUDED.source_key,
                company_key      = EXCLUDED.company_key,
                location_key     = EXCLUDED.location_key,
                category_key     = EXCLUDED.category_key,
                posted_date_key  = EXCLUDED.posted_date_key,
                scraped_date_key = EXCLUDED.scraped_date_key,
                title_raw        = EXCLUDED.title_raw,
                title_clean      = EXCLUDED.title_clean,
                salary_min       = EXCLUDED.salary_min,
                salary_max       = EXCLUDED.salary_max,
                salary_currency  = EXCLUDED.salary_currency,
                salary_period    = EXCLUDED.salary_period,
                experience_years_min = EXCLUDED.experience_years_min,
                experience_years_max = EXCLUDED.experience_years_max,
                is_remote        = EXCLUDED.is_remote,
                work_mode        = EXCLUDED.work_mode,
                employment_type  = EXCLUDED.employment_type,
                job_url          = EXCLUDED.job_url,
                run_id           = EXCLUDED.run_id,
                last_loaded_at   = now()
            RETURNING job_key, job_hash, (xmax = 0) AS inserted
        """
        result = execute_values(self.cur, sql, rows, fetch=True)

        inserted = sum(1 for _, _, ins in result if ins)
        updated = len(result) - inserted

        # Refresh the skill bridge for every touched posting (idempotent).
        job_keys = [jk for jk, _, _ in result]
        self.cur.execute(
            "DELETE FROM bridge_job_skill WHERE job_key = ANY(%s)", (job_keys,))
        bridge_rows = []
        for jk, jh, _ in result:
            for sk in skills_per_hash.get(jh, []):
                bridge_rows.append((jk, sk))
        if bridge_rows:
            execute_values(
                self.cur,
                "INSERT INTO bridge_job_skill (job_key, skill_key) VALUES %s "
                "ON CONFLICT DO NOTHING", bridge_rows)

        self._record_load(path, len(df), inserted, updated)
        self.conn.commit()
        print(f"✅ {os.path.relpath(path)}: {inserted} inserted, {updated} updated "
              f"({len(bridge_rows)} skill links)")
        return inserted, updated

    def _record_load(self, path, n_file, n_ins, n_upd):
        self.cur.execute(
            "INSERT INTO etl_load_log (file_path, rows_in_file, rows_inserted, "
            "rows_updated, loaded_at) VALUES (%s,%s,%s,%s, now()) "
            "ON CONFLICT (file_path) DO UPDATE SET rows_in_file = EXCLUDED.rows_in_file, "
            "rows_inserted = EXCLUDED.rows_inserted, rows_updated = EXCLUDED.rows_updated, "
            "loaded_at = now()", (path, n_file, n_ins, n_upd))

    # -- orchestration -------------------------------------------------
    def run(self, reload=False):
        self._prime_caches()
        silver_root = config.silver_dir()
        pattern = os.path.join(silver_root, "**", "*.csv")
        files = sorted(glob.glob(pattern, recursive=True))
        if not files:
            print(f"⚠️  No Silver CSVs found under {silver_root}/")
            return
        total_i = total_u = 0
        for path in files:
            i, u = self.load_file(path, reload=reload)
            total_i += i
            total_u += u
        print(f"\n📊 Load complete — {total_i} new postings, {total_u} updated, "
              f"across {len(files)} file(s).")

    def close(self):
        self.cur.close()
        self.conn.close()


def main():
    ap = argparse.ArgumentParser(description="Load Silver CSVs into the Postgres star schema.")
    ap.add_argument("--init", action="store_true",
                    help="create schema and seed reference data before loading")
    ap.add_argument("--reload", action="store_true",
                    help="reprocess files even if already in etl_load_log")
    args = ap.parse_args()

    loader = WarehouseLoader()
    try:
        if args.init:
            loader.init_schema()
        loader.run(reload=args.reload)
    finally:
        loader.close()


if __name__ == "__main__":
    main()
