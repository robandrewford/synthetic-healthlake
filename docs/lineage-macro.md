# Lineage Macro

The lineage macro standardizes ingestion and provenance columns across dbt models in this project.

## 1. Location

- `dbt/fhir_omop_dbt/macros/lineage.sql`

## 2. Macro Signature

```jinja
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
```

## 3. Parameters

- `ingestion_ts_expr`  
  - Expression for the ingestion/processing timestamp (default `current_timestamp`).
- `source_origin`  
  - Literal or expression describing origin, e.g. `'omop'`, `'fhir'`, `'synthetic'`, `'omop+fhir'`.
- `pipeline_run_id_expr`  
  - Expression that resolves to a pipeline run identifier; by default uses `env_var('PIPELINE_RUN_ID')` so ECS/Step Functions can inject a run id.
- `first_seen_expr`  
  - Optional expression for `lineage_first_seen_ts`. If omitted, it defaults to `ingestion_ts_expr`.
  - For Iceberg-based incremental merges, this can use a `coalesce` between existing `first_seen` and current ingestion timestamp.

## 4. Example Usage in a Model

```sql
select
    p.person_id,
    p.gender_concept_id,
    p.year_of_birth,
    {{ lineage_standard_columns(
         ingestion_ts_expr    = 'current_timestamp',
         source_origin        = "'omop'",
         pipeline_run_id_expr = "env_var('PIPELINE_RUN_ID', 'dev-run')",
         first_seen_expr      = "coalesce(lineage_first_seen_ts, current_timestamp)"
    ) }}
from {{ source('omop', 'person_iceberg') }} p
```

## 5. Integration with Iceberg Time Travel

- Iceberg tables can preserve earlier snapshots.
- `lineage_first_seen_ts` can be derived from the earliest snapshot where a record appears.
- Practically, this often means using a `coalesce(existing_first_seen_ts, current_ingestion_ts)` expression during merges.
