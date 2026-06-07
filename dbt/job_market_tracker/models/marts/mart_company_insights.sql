-- Top hiring companies: volume, breadth (categories/cities) and pay level.
select
    company_name,
    count(*)                                          as postings,
    count(distinct category_name)                     as distinct_categories,
    count(distinct governorate)                       as distinct_governorates,
    round(avg(salary_mid))                            as avg_salary_mid,
    sum(case when is_remote then 1 else 0 end)        as remote_postings,
    mode() within group (order by category_name)      as top_category,
    mode() within group (order by governorate)        as top_governorate,
    rank() over (order by count(*) desc)              as hiring_rank
from {{ ref('int_job_enriched') }}
group by company_name
order by postings desc
