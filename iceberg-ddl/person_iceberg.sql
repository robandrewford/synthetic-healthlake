CREATE TABLE IF NOT EXISTS fhir_omop.person_iceberg (
    person_id bigint,
    gender_concept_id integer,
    year_of_birth integer,
    month_of_birth integer,
    day_of_birth integer,
    birth_datetime timestamp,
    race_concept_id integer,
    ethnicity_concept_id integer,
    person_source_value varchar
)
PARTITIONED BY (year_of_birth)
LOCATION 's3://your-fhir-omop-bucket/omop/person'
TBLPROPERTIES (
    'table_type' = 'ICEBERG',
    'format' = 'PARQUET'
);
