# Iceberg DDL Overview

This project uses Apache Iceberg tables on S3 with Glue Catalog as the metastore.

## 1. Goals
- ACID properties on object storage.
- Time-travel for reproducible experiments.
- Efficient schema evolution.
- Good performance with Athena + dbt.

## 2. DDL Files

Located under `iceberg-ddl/`:

- `person_iceberg.sql`
- `fhir_patient_flat_iceberg.sql`
- `visit_occurrence_iceberg.sql`
- `condition_occurrence_iceberg.sql`
- `measurement_iceberg.sql`
- `fhir_encounter_flat_iceberg.sql`

## 3. Common Pattern

```sql
CREATE TABLE IF NOT EXISTS fhir_omop.person_iceberg (
  person_id bigint,
  gender_concept_id integer,
  year_of_birth integer,
  race_concept_id integer,
  ethnicity_concept_id integer
)
PARTITIONED BY (year_of_birth)
LOCATION 's3://<bucket>/omop/person'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format' = 'PARQUET'
);
```

## 4. Partitioning Strategy
- Persons: `year_of_birth`
- Patients: `birth_date` (or derived year)
- Visits/Encounters: date-based partitions
- Conditions/Measurements: event-date partitions

## 5. Time Travel

Iceberg supports queries “as of” a point-in-time. Platform queries can
leverage this to compare model behavior across synthetic generations.
