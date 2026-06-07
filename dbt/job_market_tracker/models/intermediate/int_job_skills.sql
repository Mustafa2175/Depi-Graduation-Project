-- One row per (job, skill): the bridge resolved to skill + job attributes,
-- so skill demand can be sliced by category, location, etc.
select
    b.job_key,
    s.skill_key,
    s.skill_name,
    s.skill_category,
    j.category_name,
    j.governorate,
    j.region,
    j.seniority,
    j.work_mode
from {{ source('warehouse', 'bridge_job_skill') }} b
inner join {{ ref('stg_skill') }}     s on b.skill_key = s.skill_key
inner join {{ ref('int_job_enriched') }} j on b.job_key = j.job_key
