# Sample Dataset Documentation

This document describes the 10,000 patient sample dataset generated for testing and demonstration purposes.

## Dataset Overview

The sample dataset contains correlated FHIR R4 and OMOP CDM v5 data:

| File | Format | Records | Size |
|------|--------|---------|------|
| `output/sample-10k/fhir/patients.ndjson` | NDJSON | 10,000 | ~5.8 MB |
| `output/sample-10k/omop/person.parquet` | Parquet | 10,000 | ~222 KB |
| `output/sample-10k/omop/condition_occurrence.parquet` | Parquet | ~15,000 | ~347 KB |
| `output/sample-10k/omop/measurement.parquet` | Parquet | ~25,000 | ~605 KB |

## Data Characteristics

### Demographics

- **Age Range**: 0-100 years
- **Gender Distribution**: ~50% male, ~50% female
- **Deceased Rate**: ~10% of patients have deceased status

### Clinical Data

- **Conditions per Patient**: 0-3 (random distribution)
  - Type 2 Diabetes (OMOP concept: 201826)
  - Essential Hypertension (OMOP concept: 320128)
  - Asthma (OMOP concept: 317009)

- **Measurements per Patient**: 0-5 (random distribution)
  - Glucose (OMOP concept: 3004501) - Range: 70-200 mg/dL
  - Systolic BP (OMOP concept: 3012888) - Range: 90-180 mmHg
  - BMI (OMOP concept: 3038553) - Range: 18-40 kg/m²

### Data Correlation

Each FHIR Patient has a corresponding OMOP Person record linked by:

- **FHIR**: `Patient.extension[omop-person-id].valueInteger` → `person_id`
- **OMOP**: `person.person_source_value` → `person-{id:06d}` matches FHIR identifier

## Generating the Dataset

### Prerequisites

```bash
# Install dependencies with uv
uv sync
```

### Generate Command

```bash
# Generate 10,000 patients (default seed=42 for reproducibility)
uv run python synthetic/generators/unified_generator.py \
    --count 10000 \
    --fhir-dir output/sample-10k/fhir \
    --omop-dir output/sample-10k/omop \
    --seed 42 \
    --format ndjson
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--count`, `-n` | 100 | Number of patients to generate |
| `--fhir-dir` | required | Output directory for FHIR data |
| `--omop-dir` | required | Output directory for OMOP Parquet files |
| `--seed` | 42 | Random seed for reproducibility |
| `--format` | json | Output format: `json` (Bundle) or `ndjson` |

### Generate Different Dataset Sizes

```bash
# Small dataset for quick tests (100 patients)
uv run python synthetic/generators/unified_generator.py \
    -n 100 --fhir-dir output/small/fhir --omop-dir output/small/omop

# Medium dataset (1,000 patients)
uv run python synthetic/generators/unified_generator.py \
    -n 1000 --fhir-dir output/medium/fhir --omop-dir output/medium/omop

# Large dataset (50,000 patients)
uv run python synthetic/generators/unified_generator.py \
    -n 50000 --fhir-dir output/large/fhir --omop-dir output/large/omop
```

## Sample Queries

### Python (Pandas)

```python
import pandas as pd
import json

# Load OMOP Person data
person_df = pd.read_parquet("output/sample-10k/omop/person.parquet")
print(f"Total patients: {len(person_df)}")

# Gender distribution
gender_dist = person_df["gender_concept_id"].value_counts()
print(f"Male (8507): {gender_dist.get(8507, 0)}")
print(f"Female (8532): {gender_dist.get(8532, 0)}")

# Age distribution (birth year)
print(f"Birth year range: {person_df['year_of_birth'].min()} - {person_df['year_of_birth'].max()}")

# Load conditions
conditions_df = pd.read_parquet("output/sample-10k/omop/condition_occurrence.parquet")
print(f"\nTotal conditions: {len(conditions_df)}")

# Condition breakdown
condition_counts = conditions_df["condition_concept_id"].value_counts()
print(f"Type 2 Diabetes (201826): {condition_counts.get(201826, 0)}")
print(f"Hypertension (320128): {condition_counts.get(320128, 0)}")
print(f"Asthma (317009): {condition_counts.get(317009, 0)}")

# Load measurements
measurements_df = pd.read_parquet("output/sample-10k/omop/measurement.parquet")
print(f"\nTotal measurements: {len(measurements_df)}")

# Measurement statistics by type
for concept_id, name in [(3004501, "Glucose"), (3012888, "Systolic BP"), (3038553, "BMI")]:
    subset = measurements_df[measurements_df["measurement_concept_id"] == concept_id]
    if not subset.empty:
        print(f"{name}: mean={subset['value_as_number'].mean():.1f}, "
              f"min={subset['value_as_number'].min():.1f}, "
              f"max={subset['value_as_number'].max():.1f}")
```

### Python (FHIR NDJSON)

```python
import json

# Read FHIR patients from NDJSON
patients = []
with open("output/sample-10k/fhir/patients.ndjson", "r") as f:
    for line in f:
        patients.append(json.loads(line))

print(f"Total FHIR patients: {len(patients)}")

# Count deceased patients
deceased = sum(1 for p in patients if "deceasedDateTime" in p)
print(f"Deceased patients: {deceased} ({deceased/len(patients)*100:.1f}%)")

# Sample patient structure
print("\nSample patient structure:")
print(json.dumps(patients[0], indent=2)[:500] + "...")
```

### SQL (Snowflake/Athena)

Once data is loaded to your data warehouse, use these queries:

```sql
-- Total patient count
SELECT COUNT(*) AS total_patients
FROM omop.person;

-- Gender distribution
SELECT
    CASE gender_concept_id
        WHEN 8507 THEN 'Male'
        WHEN 8532 THEN 'Female'
        ELSE 'Unknown'
    END AS gender,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM omop.person
GROUP BY gender_concept_id;

-- Age distribution (by decade)
SELECT
    FLOOR((EXTRACT(YEAR FROM CURRENT_DATE) - year_of_birth) / 10) * 10 AS age_decade,
    COUNT(*) AS count
FROM omop.person
GROUP BY age_decade
ORDER BY age_decade;

-- Conditions prevalence
SELECT
    c.condition_concept_id,
    CASE c.condition_concept_id
        WHEN 201826 THEN 'Type 2 Diabetes'
        WHEN 320128 THEN 'Essential Hypertension'
        WHEN 317009 THEN 'Asthma'
        ELSE 'Other'
    END AS condition_name,
    COUNT(DISTINCT c.person_id) AS patient_count,
    ROUND(COUNT(DISTINCT c.person_id) * 100.0 / (SELECT COUNT(*) FROM omop.person), 2) AS prevalence_pct
FROM omop.condition_occurrence c
GROUP BY c.condition_concept_id
ORDER BY patient_count DESC;

-- Measurement statistics
SELECT
    m.measurement_concept_id,
    CASE m.measurement_concept_id
        WHEN 3004501 THEN 'Glucose (mg/dL)'
        WHEN 3012888 THEN 'Systolic BP (mmHg)'
        WHEN 3038553 THEN 'BMI (kg/m²)'
        ELSE 'Other'
    END AS measurement_name,
    COUNT(*) AS measurement_count,
    ROUND(AVG(m.value_as_number), 2) AS avg_value,
    ROUND(MIN(m.value_as_number), 2) AS min_value,
    ROUND(MAX(m.value_as_number), 2) AS max_value
FROM omop.measurement m
GROUP BY m.measurement_concept_id
ORDER BY measurement_count DESC;

-- Patients with multiple conditions (comorbidity)
SELECT
    num_conditions,
    COUNT(*) AS patient_count
FROM (
    SELECT person_id, COUNT(DISTINCT condition_concept_id) AS num_conditions
    FROM omop.condition_occurrence
    GROUP BY person_id
) comorbidity
GROUP BY num_conditions
ORDER BY num_conditions;

-- Join FHIR and OMOP data (if both are loaded)
SELECT
    f.id AS fhir_patient_id,
    f.name[0].family AS family_name,
    f.name[0].given[0] AS given_name,
    p.year_of_birth,
    COUNT(c.condition_occurrence_id) AS condition_count
FROM fhir.patient f
JOIN omop.person p ON f.id = CAST(p.person_id AS VARCHAR)
LEFT JOIN omop.condition_occurrence c ON p.person_id = c.person_id
GROUP BY f.id, f.name[0].family, f.name[0].given[0], p.year_of_birth
ORDER BY condition_count DESC
LIMIT 20;
```

### dbt Model Example

```sql
-- models/marts/dim_patient_conditions.sql
{{ config(materialized='table') }}

WITH patient_conditions AS (
    SELECT
        p.person_id,
        p.year_of_birth,
        p.gender_concept_id,
        COUNT(DISTINCT c.condition_concept_id) AS condition_count,
        MAX(CASE WHEN c.condition_concept_id = 201826 THEN 1 ELSE 0 END) AS has_diabetes,
        MAX(CASE WHEN c.condition_concept_id = 320128 THEN 1 ELSE 0 END) AS has_hypertension,
        MAX(CASE WHEN c.condition_concept_id = 317009 THEN 1 ELSE 0 END) AS has_asthma
    FROM {{ ref('stg_person') }} p
    LEFT JOIN {{ ref('stg_condition_occurrence') }} c ON p.person_id = c.person_id
    GROUP BY p.person_id, p.year_of_birth, p.gender_concept_id
)

SELECT
    *,
    CASE
        WHEN has_diabetes + has_hypertension + has_asthma >= 2 THEN 'High Risk'
        WHEN has_diabetes + has_hypertension + has_asthma = 1 THEN 'Moderate Risk'
        ELSE 'Low Risk'
    END AS risk_category
FROM patient_conditions
```

## Loading to Cloud Data Warehouses

### Upload to S3

```bash
# Upload OMOP Parquet files to S3
aws s3 sync output/sample-10k/omop/ s3://your-bucket/omop/sample-10k/

# Upload FHIR data
aws s3 cp output/sample-10k/fhir/patients.ndjson s3://your-bucket/fhir/sample-10k/
```

### Create Snowflake Stage

```sql
-- Create stage for S3
CREATE OR REPLACE STAGE omop_stage
    URL = 's3://your-bucket/omop/sample-10k/'
    CREDENTIALS = (AWS_KEY_ID='...' AWS_SECRET_KEY='...');

-- Load person table
COPY INTO omop.person
FROM @omop_stage/person.parquet
FILE_FORMAT = (TYPE = PARQUET);

-- Load conditions
COPY INTO omop.condition_occurrence
FROM @omop_stage/condition_occurrence.parquet
FILE_FORMAT = (TYPE = PARQUET);

-- Load measurements
COPY INTO omop.measurement
FROM @omop_stage/measurement.parquet
FILE_FORMAT = (TYPE = PARQUET);
```

### Create Athena Tables (Iceberg)

```sql
-- Create external table for OMOP Person
CREATE TABLE omop.person (
    person_id BIGINT,
    gender_concept_id INT,
    year_of_birth INT,
    month_of_birth INT,
    day_of_birth INT,
    birth_datetime STRING,
    race_concept_id INT,
    ethnicity_concept_id INT,
    person_source_value STRING,
    gender_source_value STRING,
    race_source_value STRING,
    ethnicity_source_value STRING
)
STORED AS PARQUET
LOCATION 's3://your-bucket/omop/sample-10k/person/';
```

## Data Quality Notes

### Synthetic Data Limitations

1. **Random Distribution**: Conditions and measurements are randomly assigned, not based on clinical correlations
2. **Simplified Demographics**: Race and ethnicity use placeholder values
3. **No Visit Data**: visit_occurrence_id is null in all records
4. **Limited Terminology**: Only 3 condition concepts and 3 measurement concepts

### Production Considerations

For production use, consider:

- Using Synthea for more realistic clinical data
- Adding visit occurrences and drug exposures
- Implementing proper race/ethnicity mappings
- Adding observation period records

## Reproducibility

The dataset is fully reproducible using the same seed:

```bash
# Always generates identical data with seed=42
uv run python synthetic/generators/unified_generator.py \
    --count 10000 \
    --fhir-dir output/sample-10k/fhir \
    --omop-dir output/sample-10k/omop \
    --seed 42 \
    --format ndjson
```

Different seeds produce different datasets:

```bash
# Generate variant dataset with different seed
uv run python synthetic/generators/unified_generator.py \
    --count 10000 \
    --fhir-dir output/sample-10k-v2/fhir \
    --omop-dir output/sample-10k-v2/omop \
    --seed 123 \
    --format ndjson
```
