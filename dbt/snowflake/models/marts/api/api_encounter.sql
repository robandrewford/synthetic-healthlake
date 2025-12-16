{{ config(
    materialized='table',
    schema='api',
    tags=['api']
) }}

/*
API-optimized Encounter model for FHIR API endpoints.
Provides denormalized encounter data with patient context.
*/

with encounters as (
    select * from {{ ref('stg_encounter') }}
),

patients as (
    select 
        patient_id,
        full_name as patient_name,
        gender as patient_gender,
        birth_date as patient_birth_date
    from {{ ref('api_patient') }}
),

-- Join with patient data for denormalized API responses
enriched as (
    select
        e.encounter_id,
        e.status,
        e.class_code,
        e.class_display,
        e.patient_id,
        p.patient_name,
        p.patient_gender,
        e.period_start,
        e.period_end,
        e.type_code,
        e.type_display,
        e.type_system,
        e.service_provider_id,
        e.service_provider_display,
        e.reason_code,
        e.reason_display,
        e.participant_id,
        e.participant_display,
        e.location_id,
        e.location_display,
        
        -- Derived: Duration in hours
        case 
            when e.period_start is not null and e.period_end is not null then
                datediff('hour', e.period_start, e.period_end)
            else null
        end as duration_hours,
        
        -- Derived: Is active encounter
        e.status in ('in-progress', 'arrived', 'triaged', 'onleave') as is_active,
        
        -- Metadata
        e.source_file,
        e.ingestion_time
        
    from encounters e
    left join patients p on e.patient_id = p.patient_id
    where e.encounter_id is not null
)

select * from enriched
