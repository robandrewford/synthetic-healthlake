{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'patients') }}
),

renamed as (
    select
        -- Extract ID
        record_content:id::string as patient_id,

        -- Core Demographics
        record_content:active::boolean as active,
        record_content:gender::string as gender,
        record_content:birthDate::date as birth_date,
        record_content:deceasedDateTime::timestamp as deceased_datetime,

        -- Name (First element of array)
        record_content:name[0].family::string as name_family,
        record_content:name[0].given[0]::string as name_given,

        -- Address (First element)
        record_content:address[0].city::string as city,
        record_content:address[0].state::string as state,
        record_content:address[0].postalCode::string as postal_code,
        record_content:address[0].country::string as country,

        -- Metadata
        source_file,
        ingestion_time

    from source
)

select * from renamed
