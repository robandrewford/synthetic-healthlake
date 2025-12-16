{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'encounters') }}
),

renamed as (
    select
        -- Primary identifier
        record_content:id::string as encounter_id,
        
        -- Status and class
        record_content:status::string as status,
        record_content:class.code::string as class_code,
        record_content:class.display::string as class_display,
        
        -- Subject (Patient reference)
        split_part(record_content:subject.reference::string, '/', -1) as patient_id,
        record_content:subject.display::string as patient_display,
        
        -- Period
        record_content:period.start::timestamp as period_start,
        record_content:period.end::timestamp as period_end,
        
        -- Type (First element)
        record_content:type[0].coding[0].code::string as type_code,
        record_content:type[0].coding[0].display::string as type_display,
        record_content:type[0].coding[0].system::string as type_system,
        
        -- Service provider
        split_part(record_content:serviceProvider.reference::string, '/', -1) as service_provider_id,
        record_content:serviceProvider.display::string as service_provider_display,
        
        -- Reason (First element)
        record_content:reasonCode[0].coding[0].code::string as reason_code,
        record_content:reasonCode[0].coding[0].display::string as reason_display,
        
        -- Participant (Primary performer)
        split_part(record_content:participant[0].individual.reference::string, '/', -1) as participant_id,
        record_content:participant[0].individual.display::string as participant_display,
        
        -- Location (First element)
        split_part(record_content:location[0].location.reference::string, '/', -1) as location_id,
        record_content:location[0].location.display::string as location_display,
        
        -- Metadata
        source_file,
        ingestion_time
        
    from source
)

select * from renamed
