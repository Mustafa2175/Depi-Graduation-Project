select
    category_key,
    category_name,
    description as category_description
from {{ source('warehouse', 'dim_job_category') }}
