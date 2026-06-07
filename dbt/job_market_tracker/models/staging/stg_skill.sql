select
    skill_key,
    skill_name,
    skill_category
from {{ source('warehouse', 'dim_skill') }}
