# Getting Started Tutorial

This tutorial walks you through using the synthetic-healthlake project from scratch.

## What You'll Learn

By the end of this tutorial, you will:
1. Generate synthetic FHIR and OMOP data locally
2. Validate data quality
3. Transform data with dbt
4. (Optional) Deploy to AWS and run the full pipeline

**Time Required**: 30-45 minutes (local only), 1-2 hours (with AWS deployment)

## Step 1: Set Up Your Environment

### Install Prerequisites

```bash
# Check Python version (need 3.11+)
python --version

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and Install

```bash
# Clone repository
git clone https://github.com/robandrewford/synthetic-healthlake.git
cd synthetic-healthlake

# Install dependencies
uv sync

# Verify installation
uv run python -c "print('✓ Setup complete!')"
```

## Step 2: Generate Synthetic Data

### Create Your First Dataset

Let's generate data for 10 patients:

```bash
uv run python synthetic/generators/unified_generator.py \
  --count 10 \
  --fhir-dir ./my-data/fhir \
  --omop-dir ./my-data/omop \
  --seed 42
```

**What happened?**
- Created 10 correlated FHIR Patient resources
- Created matching OMOP Person records
- Generated realistic conditions and measurements
- Saved everything to `./my-data/`

### Explore the Output

```bash
# View FHIR data
cat my-data/fhir/patients_bundle.json | head -50

# View OMOP data (requires pandas)
uv run python -c "
import pandas as pd
df = pd.read_parquet('my-data/omop/person.parquet')
print(df.head())
"
```

## Step 3: Validate Data Quality

### Run Cross-Model Validation

```bash
# First, flatten FHIR to Parquet
uv run python synthetic/etl/flatten_fhir.py \
  --input-dir ./my-data/fhir \
  --output-file ./my-data/fhir/fhir_patient_flat.parquet \
  --bundle

# Validate consistency
uv run python synthetic/scripts/validate_cross_model.py \
  --omop-dir ./my-data/omop \
  --fhir-dir ./my-data/fhir
```

**Expected Output:**
```
✓ Cross-model validation passed
  OMOP persons: 10
  FHIR patients: 10
  Matched records: 10
```

## Step 4: Transform with dbt

### Run dbt Locally

```bash
cd dbt/fhir_omop_dbt

# Install dbt dependencies
dbt deps --profiles-dir .

# Load reference data
dbt seed --profiles-dir . --target dev

# Run transformations
dbt run --profiles-dir . --target dev
```

**What happened?**
- Created staging models from raw data
- Built `dim_patient` dimension table
- Built `fact_chronic_condition` fact table
- Calculated metrics

### Query the Results

```bash
uv run python -c "
import duckdb
conn = duckdb.connect('target/dev.duckdb')

# View patients
print('=== Patients ===')
print(conn.execute('SELECT * FROM dim_patient LIMIT 5').fetchdf())

# View conditions
print('\n=== Conditions ===')
print(conn.execute('SELECT * FROM fact_chronic_condition LIMIT 5').fetchdf())
"
```

## Step 5: Run the Full Pipeline

### Use the Smoke Test

The smoke test runs the entire pipeline end-to-end:

```bash
cd ../..  # Back to project root
./scripts/smoke-test.sh
```

**Expected Output:**
```
=== Pipeline Smoke Test ===
Step 1: Generate 10 synthetic patients...
✓ Generated 10 correlated FHIR/OMOP persons

Step 2: Flatten FHIR to Parquet...
✓ Flattened 10 FHIR patients to Parquet

Step 3: Validate cross-model consistency...
✓ Cross-model validation passed

Step 4: Verify output files...
  ✓ patients_bundle.json (12K)
  ✓ fhir_patient_flat.parquet (12K)
  ✓ person.parquet (12K)
  ✓ condition_occurrence.parquet (8.0K)
  ✓ measurement.parquet (8.0K)

=== ✓ Smoke Test PASSED ===
```

## Step 6: Deploy to AWS (Optional)

### Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured
- Docker installed

### Deploy Infrastructure

```bash
cd cdk

# Install CDK dependencies
npm install

# Bootstrap CDK (first time only)
npx cdk bootstrap

# Deploy
npx cdk deploy
```

**Note**: Deployment takes ~10-15 minutes. See [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md) for detailed instructions.

### Run Pipeline in AWS

```bash
# Trigger execution
aws stepfunctions start-execution \
  --state-machine-arn <your-state-machine-arn>

# Monitor in AWS Console
# Navigate to Step Functions > FhirOmopPipeline
```

### Query Results in Athena

```sql
-- Open Athena console
-- Select database: fhir_omop

SELECT * FROM dim_patient LIMIT 10;
```

## Next Steps

### Customize the Data

Edit `synthetic/generators/unified_generator.py` to:
- Add more condition types
- Include additional FHIR resources (Observation, Procedure)
- Modify demographic distributions

### Add dbt Models

Create new models in `dbt/fhir_omop_dbt/models/marts/`:
```sql
-- models/marts/dim_condition.sql
SELECT DISTINCT
  condition_concept_id,
  'Condition Name' as condition_name
FROM {{ ref('stg_condition_occurrence') }}
```

### Explore Advanced Features

- **Lineage Tracking**: View `PIPELINE_RUN_ID` in dbt models
- **Data Quality**: Add custom dbt tests
- **Metrics**: Define MetricFlow metrics
- **Security**: Review KMS encryption and VPC endpoints

## Troubleshooting

### "Module not found" errors
```bash
uv sync
```

### dbt compilation errors
```bash
cd dbt/fhir_omop_dbt
rm -rf target/
dbt compile --profiles-dir . --target dev
```

### Validation failures
- Check that FHIR and OMOP data are from the same generation run
- Verify file paths are correct

## Resources

- [Local Development Guide](../development/LOCAL_DEVELOPMENT.md)
- [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md)
- [Architecture Overview](../architecture/OVERVIEW.md)
- [FAQ](../FAQ.md)

## Congratulations! 🎉

You've successfully:
- ✅ Generated synthetic healthcare data
- ✅ Validated data quality
- ✅ Transformed data with dbt
- ✅ Run the complete pipeline

You now have a working reference architecture for FHIR-OMOP data pipelines!
