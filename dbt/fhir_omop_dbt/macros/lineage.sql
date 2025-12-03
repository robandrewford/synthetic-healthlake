{% macro lineage_standard_columns(
    ingestion_ts_expr="current_timestamp",
    source_origin="'unknown'",
    pipeline_run_id_expr="env_var('PIPELINE_RUN_ID', 'unknown')",
    first_seen_expr=None
) %}
    -- Core ingestion and lineage timestamps
    {{ ingestion_ts_expr }} as lineage_last_updated_ts,
    {% if first_seen_expr %}
        {{ first_seen_expr }} as lineage_first_seen_ts,
    {% else %}
        {{ ingestion_ts_expr }} as lineage_first_seen_ts,
    {% endif %}

    -- Pipeline run identifier passed from ECS / Step Functions via env var PIPELINE_RUN_ID
    {{ pipeline_run_id_expr }} as pipeline_run_id,

    -- Source-origin tag: e.g. 'omop', 'fhir', 'synthetic', or combined
    {{ source_origin }} as lineage_source_origin,

    -- dbt native lineage metadata
    '{{ invocation_id }}' as lineage_dbt_run_id,
    '{{ this.name }}'      as lineage_model,
    '{{ target.name }}'    as lineage_env
{% endmacro %}
