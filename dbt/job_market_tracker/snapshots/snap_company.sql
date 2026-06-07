{#
  SCD Type 2 snapshot of companies via dbt's native snapshot mechanism.
  Tracks changes to a company's raw name over time. Complements the loader's
  own SCD2 on dim_company and demonstrates the dbt-managed approach the plan
  calls for ("Configure dbt snapshots for slowly changing dimension tracking").
#}
{% snapshot snap_company %}
{{
    config(
        target_schema='snapshots',
        unique_key='company_clean',
        strategy='check',
        check_cols=['company_raw']
    )
}}
select
    company_clean,
    company_raw
from {{ source('warehouse', 'dim_company') }}
where is_current
{% endsnapshot %}
