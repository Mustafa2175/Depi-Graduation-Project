-- Job density across Egypt by governorate (and region), with pay and remote mix.
select
    region,
    governorate,
    count(*)                                                    as postings,
    count(distinct city)                                        as cities,
    count(distinct company_name)                               as hiring_companies,
    round(avg(salary_mid))                                      as avg_salary_mid,
    sum(case when is_remote then 1 else 0 end)                 as remote_postings,
    round(100.0 * count(*) / sum(count(*)) over (), 2)        as postings_share_pct
from {{ ref('int_job_enriched') }}
group by region, governorate
order by postings desc
