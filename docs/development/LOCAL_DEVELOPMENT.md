# Local Development Guide

This guide shows you how to set up and run the synthetic-healthlake project locally without deploying to AWS.

## Prerequisites

- Python 3.11 or higher
- `uv` package manager (recommended) or `pip`
- Docker (optional, for container testing)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/robandrewford/synthetic-healthlake.git
cd synthetic-healthlake
```

### 2. Install Python Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Using `pip`:
```bash
pip install -e .
```

### 3. Verify Installation

```bash
uv run python -c "from synthetic.generators import fhir_generator; print('✓ Installation successful')"
```

## Running Generators Locally

### Generate Synthetic Data

The unified generator creates correlated FHIR and OMOP data:

```bash
uv run python synthetic/generators/unified_generator.py \
  --count 100 \
  --fhir-dir ./output/fhir \
  --omop-dir ./output/omop \
  --seed 42
```

**Output:**
- `./output/fhir/patients_bundle.json` - FHIR Patient bundle
- `./output/omop/person.parquet` - OMOP Person table
- `./output/omop/condition_occurrence.parquet` - OMOP Conditions
- `./output/omop/measurement.parquet` - OMOP Measurements

### Flatten FHIR to Parquet

```bash
uv run python synthetic/etl/flatten_fhir.py \
  --input-dir ./output/fhir \
  --output-file ./output/fhir/fhir_patient_flat.parquet \
  --bundle
```

### Validate Data Quality

```bash
# Cross-model validation
uv run python synthetic/scripts/validate_cross_model.py \
  --omop-dir ./output/omop \
  --fhir-dir ./output/fhir

# Domain constraints validation
uv run python synthetic/scripts/apply_domain_constraints.py \
  --omop-dir ./output/omop \
  --fhir-dir ./output/fhir \
  --constraints-config synthetic/config/domain_constraints.yaml \
  --distributions-config synthetic/config/distribution_profiles.yaml \
  --terminology-dir synthetic/config
```

## Running dbt Locally

### Using DuckDB (No AWS Required)

The project includes a DuckDB profile for local testing:

```bash
cd dbt/fhir_omop_dbt

# Install dbt dependencies
dbt deps --profiles-dir .

# Load seed data
dbt seed --profiles-dir . --target dev

# Run models
dbt run --profiles-dir . --target dev

# Run tests
dbt test --profiles-dir . --target dev

# Generate documentation
dbt docs generate --profiles-dir . --target dev
dbt docs serve --profiles-dir . --target dev
```

### Viewing dbt Results

After running dbt, you can query the DuckDB database:

```bash
uv run python -c "
import duckdb
conn = duckdb.connect('target/dev.duckdb')
print(conn.execute('SELECT * FROM dim_patient LIMIT 5').fetchdf())
"
```

## Docker Development

### Build Images Locally

```bash
# Synthetic generator
docker build -f docker/synthetic-generator/Dockerfile -t synthetic-generator .

# dbt runner
docker build -f docker/dbt-runner/Dockerfile -t dbt-runner .
```

### Run with Docker Compose

```bash
cd docker
docker-compose up synthetic-generator
```

## Running Tests

### Python Unit Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_generators.py -v

# Run with coverage
uv run pytest tests/ --cov=synthetic --cov-report=html
```

### Integration Test (Smoke Test)

```bash
./scripts/smoke-test.sh
```

Expected output:
```
=== ✓ Smoke Test PASSED ===
All files generated successfully
```

## Development Workflow

### 1. Make Changes

Edit files in `synthetic/` or `dbt/fhir_omop_dbt/`

### 2. Test Locally

```bash
# Test generators
uv run python synthetic/generators/unified_generator.py --count 10 --fhir-dir /tmp/test-fhir --omop-dir /tmp/test-omop

# Test dbt
cd dbt/fhir_omop_dbt && dbt run --profiles-dir . --target dev
```

### 3. Run Smoke Test

```bash
./scripts/smoke-test.sh
```

### 4. Commit Changes

```bash
git add .
git commit -m "Description of changes"
```

## Troubleshooting

### Module Not Found Errors

If you see `ModuleNotFoundError: No module named 'synthetic'`:

```bash
# Reinstall in editable mode
uv sync
```

### DuckDB Errors

If dbt fails with DuckDB errors:

```bash
# Remove old database
rm dbt/fhir_omop_dbt/target/dev.duckdb

# Rerun dbt
cd dbt/fhir_omop_dbt && dbt run --profiles-dir . --target dev
```

### Permission Errors

If scripts aren't executable:

```bash
chmod +x scripts/*.sh
```

## Next Steps

- **Deploy to AWS**: See [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md)
- **Customize Generators**: Modify `synthetic/generators/` to add new data types
- **Add dbt Models**: Create new models in `dbt/fhir_omop_dbt/models/`
- **Run in Production**: Follow [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md)
