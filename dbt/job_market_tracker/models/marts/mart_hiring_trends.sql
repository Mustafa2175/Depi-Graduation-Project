-- Hiring activity over time (by posting date), monthly and by category, so
-- growth / decline can be tracked. NULL posted dates are excluded.
select
    posted_year                                          as year,
    posted_month                                         as month,
    posted_month_name                                    as month_name,
    category_name,
    count(*)                                             as postings,
    count(distinct company_name)                         as hiring_companies,
    round(avg(salary_mid))                               as avg_salary_mid
from {{ ref('int_job_enriched') }}
where posted_date is not null
group by posted_year, posted_month, posted_month_name, category_name
order by posted_year, posted_month, postings desc
