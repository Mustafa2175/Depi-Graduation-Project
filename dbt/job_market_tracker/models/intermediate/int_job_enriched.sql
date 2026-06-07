-- One denormalized row per job posting: the fact joined to every dimension.
-- This is the workhorse the marts build on.
select
    j.job_key,
    j.job_hash,
    j.title_clean,
    j.seniority,
    cat.category_name,
    co.company_name,
    loc.city,
    loc.governorate,
    loc.region,
    src.source_name,
    src.display_name        as source_display,
    j.salary_min,
    j.salary_max,
    j.salary_mid,
    j.salary_currency,
    j.experience_years_min,
    j.experience_years_max,
    j.is_remote,
    j.work_mode,
    j.employment_type,
    d.full_date             as posted_date,
    d.year                  as posted_year,
    d.quarter               as posted_quarter,
    d.month                 as posted_month,
    d.month_name            as posted_month_name,
    d.week_of_year          as posted_week,
    j.job_url,
    j.first_seen_at
from {{ ref('stg_job_postings') }} j
left join {{ ref('stg_job_category') }} cat on j.category_key = cat.category_key
left join {{ ref('stg_company') }}      co  on j.company_key  = co.company_key
left join {{ ref('stg_location') }}     loc on j.location_key = loc.location_key
left join {{ ref('stg_source') }}       src on j.source_key   = src.source_key
left join {{ ref('stg_date') }}         d   on j.posted_date_key = d.date_key
