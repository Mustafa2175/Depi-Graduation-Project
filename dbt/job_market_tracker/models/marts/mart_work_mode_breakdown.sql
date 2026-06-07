-- Remote vs hybrid vs on-site, plus employment-type mix, as two facets in
-- one tall table (facet, value, postings, share %).
with work_mode as (
    select 'work_mode' as facet, work_mode as value, count(*) as postings
    from {{ ref('int_job_enriched') }}
    group by work_mode
),
employment as (
    select 'employment_type' as facet, employment_type as value, count(*) as postings
    from {{ ref('int_job_enriched') }}
    group by employment_type
),
unioned as (
    select * from work_mode
    union all
    select * from employment
)
select
    facet,
    value,
    postings,
    round(100.0 * postings / sum(postings) over (partition by facet), 2) as share_pct
from unioned
order by facet, postings desc
