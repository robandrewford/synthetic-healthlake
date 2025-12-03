{{ config(materialized='table') }}

with person as (
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
        _ingestion_ts as omop_ingestion_ts
    from {{ ref('stg_person') }}
),
fhir_patient as (
    select
        patient_id,
        cast(person_id_omop as bigint) as person_id_omop,
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
        _ingestion_ts as fhir_ingestion_ts
    from {{ ref('stg_fhir_patient') }}
),
joined as (
    select
        p.person_id,
        p.gender_concept_id,
        p.year_of_birth,
        p.month_of_birth,
        p.day_of_birth,
        p.birth_datetime,
        p.race_concept_id,
        p.ethnicity_concept_id,
        p.person_source_value,
        p.gender_source_value,
        p.race_source_value,
        p.ethnicity_source_value,
        f.patient_id as fhir_patient_id,
        f.active as fhir_active,
        f.birth_date as fhir_birth_date,
        f.gender as fhir_gender,
        f.deceased_datetime as fhir_deceased_datetime,
        f.language as fhir_language,
        f.country as fhir_country,
        f.postal_code as fhir_postal_code,
        f.city as fhir_city,
        f.state as fhir_state,
        {{ lineage_standard_columns(
            omop_ts_col       = 'p.omop_ingestion_ts',
            fhir_ts_col       = 'f.fhir_ingestion_ts',
            synthetic_source_col = 'coalesce(f.synthetic_source, \'synthetic_unknown\')',
            pipeline_run_id_expr = "cast(null as varchar)"
        ) }}
    from person p
    left join fhir_patient f
      on p.person_id = f.person_id_omop
)
select * from joined
