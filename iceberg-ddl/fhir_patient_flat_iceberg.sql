CREATE TABLE IF NOT EXISTS fhir_omop.fhir_patient_flat_iceberg (
    patient_id varchar,
    person_id_omop bigint,
    active boolean,
    birth_date date,
    gender varchar,
    synthetic_source varchar,
    ingestion_timestamp timestamp
)
PARTITIONED BY (birth_date)
LOCATION 's3://your-fhir-omop-bucket/fhir/patient_flat'
TBLPROPERTIES (
    'table_type' = 'ICEBERG',
    'format' = 'PARQUET'
);
