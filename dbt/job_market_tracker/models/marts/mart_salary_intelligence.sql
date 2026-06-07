-- Salary intelligence by category x seniority x governorate.
-- Only postings with a known salary contribute to the aggregates.
select
    category_name,
    seniority,
    governorate,
    count(*)                                                   as postings_with_salary,
    round(min(salary_min))                                     as salary_floor,
    round(avg(salary_min))                                     as avg_salary_min,
    round(avg(salary_mid))                                     as avg_salary_mid,
    round(avg(salary_max))                                     as avg_salary_max,
    round(max(salary_max))                                     as salary_ceiling,
    round(percentile_cont(0.5) within group (order by salary_mid)) as median_salary_mid,
    max(salary_currency)                                       as currency
from {{ ref('int_job_enriched') }}
where salary_mid is not null
group by category_name, seniority, governorate
order by category_name, seniority, governorate
