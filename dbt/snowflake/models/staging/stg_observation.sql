{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'observations') }}
),

renamed as (
    select
        -- Primary identifier
        record_content:id::string as observation_id,

        -- Status
        record_content:status::string as status,

        -- Category (First element)
        record_content:category[0].coding[0].code::string as category_code,
        record_content:category[0].coding[0].display::string
            as category_display,
        record_content:category[0].coding[0].system::string as category_system,

        -- Code (LOINC or other)
        record_content:code.coding[0].code::string as code,
        record_content:code.coding[0].display::string as code_display,
        record_content:code.coding[0].system::string as code_system,

        -- Subject (Patient reference)
        record_content:subject.display::string as patient_display,
        record_content:effectiveDateTime::timestamp as effective_datetime,

        -- Encounter reference
        record_content:effectivePeriod.start::timestamp
            as effective_period_start,

        -- Effective date/time
        record_content:effectivePeriod.end::timestamp as effective_period_end,
        record_content:issued::timestamp as issued,
        record_content:valueQuantity.value::float as value_quantity,

        -- Issued
        record_content:valueQuantity.unit::string as value_unit,

        -- Value (various types)
        record_content:valueQuantity.system::string as value_system,
        record_content:valueQuantity.code::string as value_code,
        record_content:valueString::string as value_string,
        record_content:valueBoolean::boolean as value_boolean,
        record_content:valueCodeableConcept.coding[0].code::string
            as value_codeable_code,
        record_content:valueCodeableConcept.coding[0].display::string
            as value_codeable_display,
        record_content:referenceRange[0].low.value::float
            as reference_range_low,
        record_content:referenceRange[0].high.value::float
            as reference_range_high,

        -- Reference range
        record_content:referenceRange[0].low.unit::string
            as reference_range_unit,
        record_content:interpretation[0].coding[0].code::string
            as interpretation_code,
        record_content:interpretation[0].coding[0].display::string
            as interpretation_display,

        -- Interpretation
        record_content:performer[0].display::string as performer_display,
        source_file,

        -- Performer (First element)
        ingestion_time,
        split_part(record_content:subject.reference::string, '/', -1)
            as patient_id,

        -- Metadata
        split_part(record_content:encounter.reference::string, '/', -1)
            as encounter_id,
        split_part(record_content:performer[0].reference::string, '/', -1)
            as performer_id

    from source
)

select * from renamed
