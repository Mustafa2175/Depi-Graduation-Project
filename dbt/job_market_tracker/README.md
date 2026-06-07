# Phase 5 — dbt Transformation Layer

dbt turns the Phase 4 star schema into tested, documented, analytics-ready
**marts** — the tables the Phase 9 API will serve.

```
PostgreSQL star schema (public)  ──►  dbt  ──►  staging → intermediate → marts
        (Phase 4 loader)                         (views)    (views)     (tables)
```

## Layers

| Layer | Materialization | Schema | Purpose |
|-------|-----------------|--------|---------|
| **staging** | view | `staging` | 1:1 clean reads over the star-schema sources (rename, light derivation: salary mid-point, seniority bucket) |
| **intermediate** | view | `intermediate` | `int_job_enriched` (fact joined to every dim) and `int_job_skills` (job × skill) |
| **marts** | table | `marts` | analytics answers (see below) |
| **snapshots** | table | `snapshots` | `snap_company` — SCD2 history of company names via dbt |

## Marts (answers to the plan's questions)

| Mart | Question it answers |
|------|---------------------|
| `mart_in_demand_roles` | Which roles are posted most? (volume, share, saturation proxy) |
| `mart_salary_intelligence` | Salary min/avg/median/max by category × seniority × governorate |
| `mart_skill_demand` | Most requested skills overall and per category |
| `mart_company_insights` | Top hiring companies (volume, breadth, pay) |
| `mart_geographic_distribution` | Job density by governorate / region |
| `mart_work_mode_breakdown` | Remote vs hybrid vs on-site, and employment-type mix |
| `mart_hiring_trends` | Monthly hiring activity over time, by category |

## Tests & docs

`dbt build` runs **49 data tests**: `unique` / `not_null` on every key,
`accepted_values` on `work_mode` / `employment_type` / `seniority` / facets,
and `relationships` (referential integrity) from the fact to its dimensions.
Every model and key column has a `description` (browse with `dbt docs generate
&& dbt docs serve`).

## Running

The profile (`profiles.yml`) reads the same `PG*` env vars as the rest of the
project — nothing is hardcoded. From the project root:

```bash
make dbt          # dbt build (run + test + snapshot) against your database
# or, with Docker, dbt runs automatically as part of:  docker compose up --build
```

Run manually:

```bash
cd dbt/job_market_tracker
DBT_PROFILES_DIR="$PWD" dbt build      # or: dbt run / dbt test / dbt snapshot
```

> dbt requires Python 3.12 (it doesn't support 3.13/3.14 yet). `make setup`
> provisions a 3.12 virtualenv automatically; the Docker image is already 3.12.
