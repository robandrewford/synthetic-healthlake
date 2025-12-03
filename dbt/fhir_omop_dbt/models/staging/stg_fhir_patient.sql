{{ config(materialized='view') }}

with source as (
    select
        patient_id,
        person_id_omop,
        active,
        birth_date,
        gender,
        deceased_datetime,
        language,
        country,
        postal_code,
        city,
        state,
        synthetic_source,
        ingestion_timestamp,
        ingestion_timestamp as _ingestion_ts
    from {{ source('fhir', 'fhir_patient_flat_iceberg') }}
)
select * from source
