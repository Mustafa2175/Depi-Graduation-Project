# Job Market Tracker — Backend + Frontend Build Spec

**Read this whole file before writing any code.** This is a handoff spec for
Phases 9 (FastAPI backend) and 10 (React/Next.js frontend) of an existing,
fully working data engineering project. The data pipeline, warehouse, and
analytics layer are already complete and tested — your job is ONLY to build
the API and UI on top of what already exists. Do not modify anything in
`producers/`, `processing/`, `warehouse/`, `dbt/`, or `airflow/`.

## Project context

Egyptian job market data is scraped from Wuzzuf, Forasna, Jobzella, Bayt,
and Indeed, cleaned, loaded into a PostgreSQL star schema, and transformed
by dbt into 7 analytics-ready "mart" tables (schema `marts`). Airflow
automates the whole pipeline every 6 hours. Your task: expose these marts
through a REST API, then build a web dashboard that visualizes them.

## Database connection

- Engine: PostgreSQL 16
- When running inside the existing Docker Compose network (`pipeline_net`),
  the host is `db`, port `5432`.
- When running outside Docker (e.g. a locally-run FastAPI dev server), use
  `localhost:5432` (already exposed in `docker-compose.yml`).
- Credentials come from environment variables already defined in the
  project's `.env` file: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`,
  `PGDATABASE`. Reuse these exact variable names — do not invent new ones.
- All 7 tables below live in the `marts` schema (e.g. `marts.mart_salary_intelligence`).
- **Treat every mart as read-only.** The API should never INSERT/UPDATE/DELETE
  into any table — Airflow owns writing to the warehouse.

## The 7 marts (exact schema, verified from the live database)

### 1. `marts.mart_salary_intelligence`
Salary breakdown by role, seniority, and location.
| column | type | notes |
|---|---|---|
| category_name | text | job category, e.g. "Data Engineer" |
| seniority | text | Senior / Mid / Junior / Unspecified |
| governorate | text | Egyptian governorate |
| postings_with_salary | bigint | count of postings with salary data |
| salary_floor | numeric | |
| avg_salary_min | numeric | |
| avg_salary_mid | numeric | |
| avg_salary_max | numeric | |
| salary_ceiling | numeric | |
| median_salary_mid | double precision | |
| currency | text | |

### 2. `marts.mart_in_demand_roles`
Which job categories are posted most.
| column | type |
|---|---|
| category_name | text |
| postings | bigint |
| hiring_companies | bigint |
| avg_salary_mid | numeric |
| remote_postings | bigint |
| demand_share_pct | numeric |
| postings_per_company | numeric |
| demand_rank | bigint |

### 3. `marts.mart_company_insights`
Top hiring companies and their activity.
| column | type |
|---|---|
| company_name | text |
| postings | bigint |
| distinct_categories | bigint |
| distinct_governorates | bigint |
| avg_salary_mid | numeric |
| remote_postings | bigint |
| top_category | text |
| top_governorate | text |
| hiring_rank | bigint |

### 4. `marts.mart_geographic_distribution`
Job density by region/governorate.
| column | type |
|---|---|
| region | text |
| governorate | text |
| postings | bigint |
| cities | bigint |
| hiring_companies | bigint |
| avg_salary_mid | numeric |
| remote_postings | bigint |
| postings_share_pct | numeric |

### 5. `marts.mart_skill_demand`
Most requested skills per role/category.
| column | type |
|---|---|
| skill_name | text |
| skill_category | text |
| category_name | text |
| postings | bigint |
| total_postings | numeric |
| overall_skill_rank | bigint |

### 6. `marts.mart_hiring_trends`
Monthly hiring trends over time, by category.
| column | type |
|---|---|
| year | smallint |
| month | smallint |
| month_name | text |
| category_name | text |
| postings | bigint |
| hiring_companies | bigint |
| avg_salary_mid | numeric |

### 7. `marts.mart_work_mode_breakdown`
Remote / hybrid / on-site distribution (also covers employment type via `facet`).
| column | type |
|---|---|
| facet | text | either "work_mode" or "employment_type" |
| value | text | e.g. "remote", "hybrid", "on_site", "full_time" |
| postings | bigint |
| share_pct | numeric |

## Backend requirements (Phase 9 — FastAPI)

Tech: **FastAPI**, connecting to PostgreSQL via SQLAlchemy (already a
project dependency) or psycopg2. Containerize with Docker, matching the
existing project's Docker conventions (see `Dockerfile` and
`docker-compose.yml` for patterns already in use — e.g. reading `PG*` env
vars, joining the same `pipeline_net` network as `db`).

Build one GET endpoint per mart, with sensible query-parameter filtering
and pagination on all of them. Suggested routes:

- `GET /api/salary-intelligence` — filters: `category`, `seniority`, `governorate`
- `GET /api/in-demand-roles` — filters: `limit` (top N by `demand_rank`)
- `GET /api/company-insights` — filters: `limit` (top N by `hiring_rank`), `governorate`
- `GET /api/geographic-distribution` — filters: `region`
- `GET /api/skill-demand` — filters: `category`, `limit`
- `GET /api/hiring-trends` — filters: `category`, `year`
- `GET /api/work-mode-breakdown` — filters: `facet`
- `GET /api/health` — simple DB connectivity check, useful for debugging

Response format: JSON arrays of objects, one object per row, using the
exact column names from the tables above (no renaming needed).

Add CORS middleware allowing the frontend's origin (localhost during dev).
Add basic input validation (e.g. reject unreasonable `limit` values) and
auto-generated docs via FastAPI's built-in `/docs` (Swagger UI) — this is
free with FastAPI and very useful for testing without a frontend.

No authentication is required for this project (public read-only analytics).

## Frontend requirements (Phase 10 — React/Next.js + Tailwind)

Build a dashboard that calls the API above. Suggested pages:

1. **Home / overview** — key stats pulled from `in-demand-roles` and
   `work-mode-breakdown` (e.g. total postings, top category, remote %)
2. **Salary explorer** — filterable table/chart from `salary-intelligence`
   (filter by category, seniority, governorate)
3. **Job demand page** — bar chart of `in-demand-roles`, ranked
4. **Company profiles** — table from `company-insights`, sortable by `hiring_rank`
5. **Skills trends page** — top skills from `skill-demand`, grouped by category
6. **Geographic view** — table or map-style breakdown from `geographic-distribution`
7. **Hiring trends over time** — line chart from `hiring-trends`, by month/category

Charting library: any of Recharts, Chart.js, or similar — pick one and use
it consistently.

## Practical setup details (read this before writing code)

- **Folder locations**: create the backend in a new top-level `api/` folder,
  and the frontend in a new top-level `frontend/` folder. Do not mix new
  code into `producers/`, `processing/`, `warehouse/`, `dbt/`, or `airflow/`.
- **Ports already in use — do not reuse these**: `5432` (Postgres),
  `8080` (Airflow webserver). Suggested new ports: `8000` for the FastAPI
  backend, `3000` for the frontend dev server.
- **Read `.env.example` and `.env` (if present) first** to see the exact
  env var names already established in this project (`PGHOST`, `PGPORT`,
  `PGUSER`, `PGPASSWORD`, `PGDATABASE`) before writing any config — reuse
  them exactly, don't invent new variable names for the same values.
- **Test against the real, live database**, not mocked data. Bring up the
  existing stack first (`docker compose -f docker-compose.yml -f
  docker-compose.airflow.yml up -d db`) and query the actual `marts` schema
  to confirm every endpoint returns real rows before considering it done.
- **Start the backend first, verify it fully, then start the frontend.**
  Don't build both simultaneously — verifying the API works via `/docs`
  before writing any frontend code avoids debugging two layers at once.
- If Docker Desktop isn't running, `docker compose` commands will fail with
  a connection error (`open //./pipe/dockerDesktopLinuxEngine`) — this
  means start Docker Desktop first, it's not a code problem.


After building, the person testing this will only do two things:
1. Open the FastAPI docs at `http://localhost:<port>/docs` and confirm each
   endpoint returns real data (not an error) when clicked "Try it out"
2. Open the frontend in a browser and confirm each page shows real numbers,
   not blank/broken sections

If either fails, fix it before considering the phase done — don't leave
partially-working endpoints or pages.

## Do NOT touch

- `producers/`, `processing/`, `warehouse/`, `dbt/`, `airflow/` — these are
  complete, tested, and out of scope
- Do not add new tables, views, or modify the `marts` schema — if a metric
  seems missing, ask rather than modifying dbt models
- Do not change `docker-compose.yml` or `docker-compose.airflow.yml` — add
  new services (e.g. `api`, `frontend`) via a new
  `docker-compose.app.yml` override file instead, following the same
  additive-override pattern already used for `docker-compose.airflow.yml`
