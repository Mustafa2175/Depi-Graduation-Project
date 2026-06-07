select
    source_key,
    source_name,
    display_name,
    base_url
from {{ source('warehouse', 'dim_source') }}
