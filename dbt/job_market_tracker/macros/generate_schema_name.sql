{#
  Use custom schema names verbatim (staging / intermediate / marts / snapshots)
  instead of dbt's default "<target_schema>_<custom>" concatenation, so the
  warehouse layout stays predictable and readable.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
