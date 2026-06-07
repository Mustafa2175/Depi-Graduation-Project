-- Most requested skills overall and per category.
with per_skill_category as (
    select
        skill_name,
        skill_category,
        category_name,
        count(distinct job_key) as postings
    from {{ ref('int_job_skills') }}
    group by skill_name, skill_category, category_name
),
totals as (
    select skill_name, sum(postings) as total_postings
    from per_skill_category
    group by skill_name
)
select
    p.skill_name,
    p.skill_category,
    p.category_name,
    p.postings,
    t.total_postings,
    rank() over (order by t.total_postings desc, p.skill_name) as overall_skill_rank
from per_skill_category p
join totals t using (skill_name)
order by t.total_postings desc, p.skill_name, p.postings desc
