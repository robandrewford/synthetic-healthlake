{{ config(materialized='view') }}

with source as (
    select
        person_id,
        gender_concept_id,
        year_of_birth,
        month_of_birth,
        day_of_birth,
        birth_datetime,
        race_concept_id,
        ethnicity_concept_id,
        person_source_value,
        gender_source_value,
        race_source_value,
        ethnicity_source_value,
        current_timestamp as _ingestion_ts
    from {{ source('omop', 'person_iceberg') }}
)
select * from source
