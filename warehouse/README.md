# Phase 4 — Data Modeling & PostgreSQL Star Schema (Gold Layer)

This directory takes the **Silver** layer (cleaned CSVs in `data/silver/`)
and loads it into a **PostgreSQL star schema** — the analytics-ready Gold
layer that Phase 7 (analytics) and Phase 9 (the API) build on.

```
data/silver/**/*.csv  ──►  warehouse/load_to_postgres.py  ──►  PostgreSQL star schema
```

## Files

| File | Purpose |
|------|---------|
| `sql/01_schema.sql` | DDL: all dimensions, the fact table, indexes, constraints |
| `sql/02_seed.sql`   | Reference/seed data: governorates, sources, categories, skills |
| `config.py`         | DB connection from env vars (`PG*`) with local defaults |
| `load_to_postgres.py` | The loader: Silver CSV → star schema (idempotent, incremental) |
| `make_sample_data.py` | Generates realistic sample Silver CSVs for testing |
| `make_raw_data.py`  | Generates raw Bronze JSON (with descriptions) for the full-pipeline test |
| `test_phase4.py`    | Warehouse test: rebuild → load crafted Silver → assert invariants → analytics |
| `test_pipeline.py`  | Full Bronze→Silver→Gold test: runs the real cleaning pipeline, then loads |

## The star schema

**Fact** — `fact_job_postings` (grain: one row per unique job posting,
deduplicated by `job_hash`). Includes `work_mode` (remote/hybrid/on-site) and
`employment_type` (full-time/part-time/contract/internship/freelance), both
classified by the cleaning layer.

**Dimensions**
- `dim_date` — calendar attributes (year/quarter/month/week, `is_weekend` = Fri/Sat)
- `dim_source` — the job board (Wuzzuf, Bayt, Indeed, Forasna, Jobzella)
- `dim_location` — city + governorate (SCD Type 1)
- `dim_company` — **SCD Type 2**: keeps history via `valid_from` / `valid_to` / `is_current`
- `dim_job_category` — seeded categories; `keywords[]` drive title → category mapping
- `dim_skill` + `bridge_job_skill` — many-to-many skills per posting
- `ref_governorate` — Egyptian governorates lookup (FK target for locations)
- `etl_load_log` — which Silver files have been loaded (incremental bookkeeping)

```
                         dim_date ─┐
            dim_source ─┐          │
           dim_company ─┤          │      ┌─ dim_job_category
          dim_location ─┴── fact_job_postings ──┤
                                   │            └─ bridge_job_skill ── dim_skill
                         dim_date ─┘
```

## How to run

Prerequisites: a running PostgreSQL and `pip install pandas psycopg2-binary sqlalchemy`.

```bash
export PYTHONPATH=$PYTHONPATH:.

# Connection (defaults shown; override via environment if needed)
export PGHOST=localhost PGPORT=5432 PGDATABASE=job_market_tracker
# export PGUSER=...  PGPASSWORD=...

# First time: create the DB if it doesn't exist
createdb job_market_tracker     # or: psql -c "CREATE DATABASE job_market_tracker;"

# Build schema + seed, then load every Silver CSV
python3 warehouse/load_to_postgres.py --init

# Later runs: incremental — only new files are processed
python3 warehouse/load_to_postgres.py

# Reprocess everything (still no duplicates — upsert on job_hash)
python3 warehouse/load_to_postgres.py --reload
```

### Testing without live scraping

`data/` is git-ignored and may be empty. Generate sample Silver data and run
the full end-to-end test:

```bash
export PYTHONPATH=$PYTHONPATH:.
python3 warehouse/make_sample_data.py     # writes data/silver/**/*.csv
python3 warehouse/test_phase4.py          # rebuilds, loads, asserts, prints analytics
```

The test verifies (14 checks): fact count == unique `job_hash`, no duplicate
hashes, cross-source duplicates collapse to one row, no orphan/NULL foreign
keys, every governorate is known, SCD2 history is kept correctly, titles get
categorised, skills are bridged, dates resolve, and **idempotency** (re-running
and force-reloading add zero rows).

## Design notes

- **Deduplication** is centred on `job_hash` (generated upstream as a fingerprint
  of title + company + city). The fact upsert uses `ON CONFLICT (job_hash)`, so
  the same posting appearing on multiple boards — or the pipeline re-running —
  collapses to a single fact row.
- **SCD Type 2** on `dim_company`: when a company's raw name changes, the current
  row is closed (`valid_to`, `is_current = false`) and a new version is opened.
  A partial unique index guarantees exactly one current row per company.
- **Categorisation** keeps the DB as the single source of truth: the loader reads
  `dim_job_category.keywords` and scores each title, so categories can be tuned
  by editing the seed alone.
- **Skills** are extracted by the **cleaning layer** (`processing/utils/skills.py`)
  from the job title *and description*, and written to the Silver `skills` column
  (pipe-delimited, canonical names matching `dim_skill`). The loader reads that
  column, auto-creates any unseen skill, and links it via `bridge_job_skill`.
  (A title-only fallback remains for legacy Silver files without the column.)

## Testing matrix

| Test | Scope | What it proves |
|------|-------|----------------|
| `test_phase4.py`   | Warehouse only (crafted Silver) | dedup, SCD2, FK integrity, idempotency, categorisation |
| `test_pipeline.py` | Bronze→Silver→Gold (real pipeline) | skills from descriptions, job-type classification, quality-gate quarantine, real Silver loads end-to-end |

## Next phase

With the Gold layer populated, the project is ready for **Phase 5 (dbt
transformation layer)** and **Phase 7 (analytics models)** — the sample queries
printed by the tests are an early preview of those insights.
