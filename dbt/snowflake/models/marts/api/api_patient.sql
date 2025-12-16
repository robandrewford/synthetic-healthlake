{{ config(
    materialized='table',
    schema='api',
    tags=['api']
) }}

/*
API-optimized Patient model for FHIR API endpoints.
Provides denormalized patient data ready for JSON response generation.
*/

with patients as (
    select * from {{ ref('stg_patient') }}
),

-- Calculate derived fields
enriched as (
    select
        patient_id,
        active,
        gender,
        birth_date,
        deceased_datetime,
        name_family,
        name_given,
        city,
        state,
        postal_code,
        country,
        
        -- Derived: Full name
        concat_ws(' ', name_given, name_family) as full_name,
        
        -- Derived: Age calculation
        case 
            when deceased_datetime is not null then
                datediff('year', birth_date, deceased_datetime::date)
            else
                datediff('year', birth_date, current_date())
        end as age,
        
        -- Derived: Is deceased flag
        deceased_datetime is not null as is_deceased,
        
        -- Metadata for debugging/auditing
        source_file,
        ingestion_time
        
    from patients
    where patient_id is not null
)

select * from enriched
