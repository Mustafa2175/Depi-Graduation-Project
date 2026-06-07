-- All company versions (SCD Type 2). Keyed by the unique company_key, so a
-- fact row always resolves to the exact version it was loaded against —
-- including historical (non-current) versions. Use `is_current` to filter to
-- the live record when you need one row per company.
select
    company_key,
    company_clean as company_name,
    company_raw,
    valid_from,
    valid_to,
    is_current
from {{ source('warehouse', 'dim_company') }}
