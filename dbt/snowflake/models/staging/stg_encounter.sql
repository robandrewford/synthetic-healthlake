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
        record_content:subject.display::string as patient_display,
        record_content:period.start::timestamp as period_start,

        -- Period
        record_content:period.end::timestamp as period_end,
        record_content:type[0].coding[0].code::string as type_code,

        -- Type (First element)
        record_content:type[0].coding[0].display::string as type_display,
        record_content:type[0].coding[0].system::string as type_system,
        record_content:serviceProvider.display::string
            as service_provider_display,

        -- Service provider
        record_content:reasonCode[0].coding[0].code::string as reason_code,
        record_content:reasonCode[0].coding[0].display::string
            as reason_display,

        -- Reason (First element)
        record_content:participant[0].individual.display::string
            as participant_display,
        record_content:location[0].location.display::string as location_display,

        -- Participant (Primary performer)
        source_file,
        ingestion_time,

        -- Location (First element)
        split_part(record_content:subject.reference::string, '/', -1)
            as patient_id,
        split_part(record_content:serviceProvider.reference::string, '/', -1)
            as service_provider_id,

        -- Metadata
        split_part(
            record_content:participant[0].individual.reference::string, '/', -1
        ) as participant_id,
        split_part(
            record_content:location[0].location.reference::string, '/', -1
        ) as location_id

    from source
)

select * from renamed
