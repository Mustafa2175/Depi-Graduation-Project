-- In-demand roles: posting volume by category, with salary context and a
-- simple saturation proxy (postings per distinct hiring company).
with by_category as (
    select
        category_name,
        count(*)                                   as postings,
        count(distinct company_name)               as hiring_companies,
        round(avg(salary_mid))                      as avg_salary_mid,
        sum(case when is_remote then 1 else 0 end) as remote_postings
    from {{ ref('int_job_enriched') }}
    group by category_name
)
select
    category_name,
    postings,
    hiring_companies,
    avg_salary_mid,
    remote_postings,
    round(100.0 * postings / sum(postings) over (), 2)              as demand_share_pct,
    round(postings::numeric / nullif(hiring_companies, 0), 2)       as postings_per_company,
    rank() over (order by postings desc)                           as demand_rank
from by_category
order by postings desc
