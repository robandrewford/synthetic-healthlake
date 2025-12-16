{{ config(
    materialized='table',
    schema='api',
    tags=['api']
) }}

/*
API-optimized Observation model for FHIR API endpoints.
Provides denormalized observation data with patient/encounter context.
*/

with observations as (
    select * from {{ ref('stg_observation') }}
),

patients as (
    select
        patient_id,
        full_name as patient_name
    from {{ ref('api_patient') }}
),

encounters as (
    select
        encounter_id,
        class_display as encounter_class
    from {{ ref('stg_encounter') }}
),

-- Join and enrich observation data
enriched as (
    select
        o.observation_id,
        o.status,
        o.category_code,
        o.category_display,
        o.code,
        o.code_display,
        o.code_system,
        o.patient_id,
        p.patient_name,
        o.encounter_id,
        e.encounter_class,
        o.effective_datetime,
        o.effective_period_start,
        o.effective_period_end,
        o.issued,

        -- Value fields (coalesced for easier API handling)
        o.value_quantity,
        o.value_unit,
        o.value_string,
        o.value_boolean,
        o.value_codeable_code,
        o.value_codeable_display,

        -- Formatted value for display
        o.reference_range_low,

        -- Reference range
        o.reference_range_high,
        o.reference_range_unit,
        o.interpretation_code,

        -- Interpretation
        o.interpretation_display,
        o.performer_id,

        -- Derived: Is abnormal flag
        o.performer_display,

        -- Derived: Category type for filtering
        o.source_file,

        -- Performer info
        o.ingestion_time,
        case
            when o.value_quantity is not null
                then
                    concat(
                        o.value_quantity::string,
                        ' ',
                        coalesce(o.value_unit, '')
                    )
            when o.value_string is not null
                then
                    o.value_string
            when o.value_boolean is not null
                then
                    case when o.value_boolean then 'Yes' else 'No' end
            when o.value_codeable_display is not null
                then
                    o.value_codeable_display
        end as value_display,

        -- Metadata
        case
            when
                o.interpretation_code in ('H', 'HH', 'L', 'LL', 'A', 'AA')
                then true
            when
                o.value_quantity is not null
                and o.reference_range_low is not null
                and o.reference_range_high is not null
                then
                    o.value_quantity < o.reference_range_low
                    or o.value_quantity > o.reference_range_high
            else false
        end as is_abnormal,
        case
            when o.category_code = 'vital-signs' then 'vital-signs'
            when o.category_code = 'laboratory' then 'laboratory'
            when o.category_code = 'imaging' then 'imaging'
            when o.category_code = 'procedure' then 'procedure'
            when o.category_code = 'survey' then 'survey'
            when o.category_code = 'exam' then 'exam'
            when o.category_code = 'therapy' then 'therapy'
            when o.category_code = 'activity' then 'activity'
            else 'other'
        end as category_type

    from observations as o
    left join patients as p on o.patient_id = p.patient_id
    left join encounters as e on o.encounter_id = e.encounter_id
    where o.observation_id is not null
)

select * from enriched
