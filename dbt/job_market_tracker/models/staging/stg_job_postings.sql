-- Staging: one clean row per job posting, with a derived salary mid-point
-- and a seniority bucket parsed from the title.
with src as (
    select * from {{ source('warehouse', 'fact_job_postings') }}
)
select
    job_key,
    job_hash,
    source_job_id,
    source_key,
    company_key,
    location_key,
    category_key,
    posted_date_key,
    scraped_date_key,
    title_clean,
    title_raw,
    salary_min,
    salary_max,
    case
        when salary_min is not null and salary_max is not null
            then round((salary_min + salary_max) / 2.0, 2)
        when salary_min is not null then salary_min
        when salary_max is not null then salary_max
    end                                             as salary_mid,
    salary_currency,
    salary_period,
    experience_years_min,
    experience_years_max,
    coalesce(is_remote, false)                      as is_remote,
    coalesce(work_mode, 'on-site')                  as work_mode,
    coalesce(employment_type, 'full-time')          as employment_type,
    case
        when title_clean ilike '%senior%' or title_clean ilike '%lead%'
             or title_clean ilike '%principal%' or title_clean ilike '%staff%' then 'Senior'
        when title_clean ilike '%junior%' or title_clean ilike '%entry%'
             or title_clean ilike '%intern%' or title_clean ilike '%trainee%' then 'Junior'
        when title_clean ilike '%mid%' then 'Mid'
        else 'Unspecified'
    end                                             as seniority,
    job_url,
    run_id,
    first_seen_at,
    last_loaded_at
from src
