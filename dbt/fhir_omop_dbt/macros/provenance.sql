{% macro lineage_standard_columns(
    omop_ts_col='omop_ingestion_ts',
    fhir_ts_col='fhir_ingestion_ts',
    synthetic_source_col='synthetic_source',
    pipeline_run_id_expr="cast(null as varchar)"
) %}
    {{ omop_ts_col }} as omop_ingestion_ts,
    {{ fhir_ts_col }} as fhir_ingestion_ts,

    least(
        {{ omop_ts_col }},
        coalesce({{ fhir_ts_col }}, {{ omop_ts_col }})
    ) as lineage_first_seen_ts,

    greatest(
        {{ omop_ts_col }},
        coalesce({{ fhir_ts_col }}, {{ omop_ts_col }})
    ) as lineage_last_updated_ts,

    case
        when {{ fhir_ts_col }} is not null then 'omop+fhir'
        else 'omop_only'
    end as lineage_sources,

    {{ synthetic_source_col }} as synthetic_source,

    {{ pipeline_run_id_expr }} as pipeline_run_id
{% endmacro %}
