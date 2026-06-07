-- =====================================================================
-- Job Market Tracker  ·  Phase 4 — PostgreSQL Star Schema (DDL)
-- Gold layer: dimensional model fed from the Silver CSVs.
--
-- Grain of the fact table: one row per unique job posting (deduplicated
-- by job_hash, which is generated upstream as a fingerprint of
-- title + company + city).
--
-- This script is idempotent — safe to run repeatedly.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Reference lookup: Egyptian governorates (seeded in 02_seed.sql)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ref_governorate (
    governorate     TEXT PRIMARY KEY,
    region          TEXT          -- Greater Cairo / Delta / Upper Egypt / Canal / Coastal
);

-- ---------------------------------------------------------------------
-- Date dimension
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key        INTEGER PRIMARY KEY,        -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    month_name      TEXT NOT NULL,
    day             SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL,          -- 1 = Monday … 7 = Sunday (ISO)
    day_name        TEXT NOT NULL,
    week_of_year    SMALLINT NOT NULL,
    is_weekend      BOOLEAN NOT NULL            -- Fri/Sat in Egypt
);

-- ---------------------------------------------------------------------
-- Source dimension (the job board the posting came from)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_source (
    source_key      SERIAL PRIMARY KEY,
    source_name     TEXT NOT NULL UNIQUE,
    display_name    TEXT,
    base_url        TEXT
);

-- ---------------------------------------------------------------------
-- Location dimension (SCD Type 1 — locations don't change identity)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_location (
    location_key    SERIAL PRIMARY KEY,
    location_city   TEXT NOT NULL,
    location_gov    TEXT NOT NULL,
    CONSTRAINT uq_location UNIQUE (location_city, location_gov),
    CONSTRAINT fk_location_gov FOREIGN KEY (location_gov)
        REFERENCES ref_governorate (governorate)
        DEFERRABLE INITIALLY DEFERRED
);

-- ---------------------------------------------------------------------
-- Company dimension (SCD Type 2 — company attributes can change over
-- time; we keep history with valid_from / valid_to / is_current).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_company (
    company_key     SERIAL PRIMARY KEY,
    company_clean   TEXT NOT NULL,              -- natural / business key
    company_raw     TEXT,
    valid_from      DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to        DATE,                       -- NULL = still current
    is_current      BOOLEAN NOT NULL DEFAULT TRUE
);
-- Only one current row per company name.
CREATE UNIQUE INDEX IF NOT EXISTS uq_company_current
    ON dim_company (company_clean) WHERE is_current;

-- ---------------------------------------------------------------------
-- Job category dimension (seeded reference; keywords drive title -> category)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_job_category (
    category_key    SERIAL PRIMARY KEY,
    category_name   TEXT NOT NULL UNIQUE,
    keywords        TEXT[] NOT NULL DEFAULT '{}',
    description     TEXT
);

-- ---------------------------------------------------------------------
-- Skill dimension + bridge (many-to-many with job postings)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_skill (
    skill_key       SERIAL PRIMARY KEY,
    skill_name      TEXT NOT NULL UNIQUE,
    skill_category  TEXT                        -- language / framework / cloud / db / tool
);

-- ---------------------------------------------------------------------
-- Fact: job postings
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_job_postings (
    job_key                 BIGSERIAL PRIMARY KEY,
    job_hash                TEXT NOT NULL UNIQUE,       -- dedup business key
    source_job_id           TEXT,

    -- Foreign keys to dimensions
    source_key              INTEGER NOT NULL REFERENCES dim_source (source_key),
    company_key             INTEGER NOT NULL REFERENCES dim_company (company_key),
    location_key            INTEGER NOT NULL REFERENCES dim_location (location_key),
    category_key            INTEGER NOT NULL REFERENCES dim_job_category (category_key),
    posted_date_key         INTEGER REFERENCES dim_date (date_key),
    scraped_date_key        INTEGER REFERENCES dim_date (date_key),

    -- Degenerate / descriptive attributes
    title_raw               TEXT,
    title_clean             TEXT,

    -- Measures
    salary_min              NUMERIC(12,2),
    salary_max              NUMERIC(12,2),
    salary_currency         TEXT,
    salary_period           TEXT,           -- hourly | daily | weekly | monthly | yearly
    experience_years_min    SMALLINT,
    experience_years_max    SMALLINT,
    is_remote               BOOLEAN DEFAULT FALSE,
    work_mode               TEXT,           -- remote | hybrid | on-site
    employment_type         TEXT,           -- full-time | part-time | contract | internship | freelance

    job_url                 TEXT,
    run_id                  TEXT,
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_loaded_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_salary_range CHECK (
        salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min
    )
);

-- Idempotent column adds for pre-existing warehouses (CREATE TABLE IF NOT
-- EXISTS above won't alter a table that already exists).
ALTER TABLE fact_job_postings ADD COLUMN IF NOT EXISTS salary_period TEXT;

CREATE TABLE IF NOT EXISTS bridge_job_skill (
    job_key         BIGINT NOT NULL REFERENCES fact_job_postings (job_key) ON DELETE CASCADE,
    skill_key       INTEGER NOT NULL REFERENCES dim_skill (skill_key),
    PRIMARY KEY (job_key, skill_key)
);

-- ---------------------------------------------------------------------
-- ETL bookkeeping: which Silver files have already been loaded
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_load_log (
    file_path       TEXT PRIMARY KEY,
    rows_in_file    INTEGER,
    rows_inserted   INTEGER,
    rows_updated    INTEGER,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Performance indexes on the fact's foreign keys & common filters
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_fact_source       ON fact_job_postings (source_key);
CREATE INDEX IF NOT EXISTS ix_fact_company      ON fact_job_postings (company_key);
CREATE INDEX IF NOT EXISTS ix_fact_location     ON fact_job_postings (location_key);
CREATE INDEX IF NOT EXISTS ix_fact_category     ON fact_job_postings (category_key);
CREATE INDEX IF NOT EXISTS ix_fact_posted_date  ON fact_job_postings (posted_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_is_remote    ON fact_job_postings (is_remote);
CREATE INDEX IF NOT EXISTS ix_fact_work_mode    ON fact_job_postings (work_mode);
CREATE INDEX IF NOT EXISTS ix_fact_emp_type     ON fact_job_postings (employment_type);
CREATE INDEX IF NOT EXISTS ix_bridge_skill      ON bridge_job_skill (skill_key);

-- ---------------------------------------------------------------------
-- Forward-compatible upgrades (no-ops on a fresh build; add columns to
-- an existing fact table created before work_mode / employment_type).
-- ---------------------------------------------------------------------
ALTER TABLE fact_job_postings ADD COLUMN IF NOT EXISTS work_mode TEXT;
ALTER TABLE fact_job_postings ADD COLUMN IF NOT EXISTS employment_type TEXT;
