#!/bin/bash
set -euo pipefail

# dbt Pipeline Script for ECS
# Runs dbt transformations with PIPELINE_RUN_ID from Step Functions

echo "=== dbt Pipeline ==="
echo "PIPELINE_RUN_ID: ${PIPELINE_RUN_ID:-not-set}"
echo "S3_DATA_BUCKET: ${S3_DATA_BUCKET:-not-set}"
echo "GLUE_DB_NAME: ${GLUE_DB_NAME:-fhir_omop}"
echo "DBT_TARGET: ${DBT_TARGET:-dev}"

# Set defaults
PIPELINE_RUN_ID=${PIPELINE_RUN_ID:-local-$(date +%Y%m%d-%H%M%S)}
DBT_TARGET=${DBT_TARGET:-dev}

# Export PIPELINE_RUN_ID for dbt to use in lineage macro
export PIPELINE_RUN_ID

cd /app/dbt/fhir_omop_dbt

echo "Step 1: Installing dbt dependencies..."
dbt deps --profiles-dir .

echo "Step 2: Loading seed data..."
dbt seed --profiles-dir . --target "${DBT_TARGET}"

echo "Step 3: Running dbt models..."
dbt run --profiles-dir . --target "${DBT_TARGET}"

echo "Step 4: Running dbt tests..."
dbt test --profiles-dir . --target "${DBT_TARGET}" || echo "⚠ Some tests failed"

# Upload dbt artifacts to S3 if bucket is configured
if [ -n "${S3_DATA_BUCKET:-}" ]; then
  S3_PREFIX="s3://${S3_DATA_BUCKET}/runs/${PIPELINE_RUN_ID}/dbt"

  echo "Step 5: Uploading dbt artifacts to S3: ${S3_PREFIX}"

  aws s3 cp target/manifest.json "${S3_PREFIX}/manifest.json" || true
  aws s3 cp target/run_results.json "${S3_PREFIX}/run_results.json" || true

  echo "✓ dbt artifacts uploaded"
else
  echo "⚠ S3_DATA_BUCKET not set, skipping artifact upload"
fi

echo "=== dbt Pipeline Complete ==="
echo "PIPELINE_RUN_ID used for lineage: ${PIPELINE_RUN_ID}"
