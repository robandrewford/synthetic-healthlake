{{ config(materialized='table') }}

with cond as (
    select
        c.person_id,
        c.condition_concept_id,
        c.condition_start_date,
        c.visit_occurrence_id
    from {{ source('omop', 'condition_occurrence_iceberg') }} c
),
cond_with_group as (
    select
        c.person_id,
        c.condition_start_date,
        c.visit_occurrence_id,
        cc.chronic_condition_code,
        cc.chronic_condition_name
    from cond c
    join {{ ref('chronic_condition_concepts') }} cc
      on c.condition_concept_id = cc.condition_concept_id
),
cond_agg as (
    select
        person_id,
        chronic_condition_code,
        max(chronic_condition_name) as chronic_condition_name,
        min(condition_start_date) as first_diagnosis_date,
        max(condition_start_date) as last_diagnosis_date,
        count(*) as diagnosis_count,
        count(distinct visit_occurrence_id) as encounter_count
    from cond_with_group
    group by person_id, chronic_condition_code
),
measurement_agg as (
    select
        m.person_id,
        cc.chronic_condition_code,
        count(*) as measurement_count
    from {{ source('omop', 'measurement_iceberg') }} m
    join {{ ref('chronic_condition_concepts') }} cc
      on m.measurement_concept_id = cc.condition_concept_id
    group by m.person_id, cc.chronic_condition_code
),
joined as (
    select
        d.person_id,
        ca.chronic_condition_code,
        ca.chronic_condition_name,
        ca.first_diagnosis_date,
        ca.last_diagnosis_date,
        ca.diagnosis_count,
        ca.encounter_count,
        coalesce(ma.measurement_count, 0) as measurement_count,
        d.gender_concept_id,
        d.year_of_birth,
        d.race_concept_id,
        d.ethnicity_concept_id,
        d.omop_ingestion_ts,
        d.fhir_ingestion_ts,
        d.synthetic_source,
        {{ lineage_standard_columns(
            omop_ts_col       = 'd.omop_ingestion_ts',
            fhir_ts_col       = 'd.fhir_ingestion_ts',
            synthetic_source_col = 'd.synthetic_source',
            pipeline_run_id_expr = "cast(null as varchar)"
        ) }}
    from {{ ref('dim_patient') }} d
    join cond_agg ca
      on d.person_id = ca.person_id
    left join measurement_agg ma
      on d.person_id = ma.person_id
     and ca.chronic_condition_code = ma.chronic_condition_code
)
select * from joined
