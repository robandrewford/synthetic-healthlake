#!/bin/bash
set -euo pipefail

# Synthetic Data Pipeline Script for ECS
# Generates synthetic FHIR/OMOP data and uploads to S3

echo "=== Synthetic Data Pipeline ==="
echo "PIPELINE_RUN_ID: ${PIPELINE_RUN_ID:-not-set}"
echo "S3_DATA_BUCKET: ${S3_DATA_BUCKET:-not-set}"
echo "PATIENT_COUNT: ${PATIENT_COUNT:-100}"

# Set defaults
PIPELINE_RUN_ID=${PIPELINE_RUN_ID:-local-$(date +%Y%m%d-%H%M%S)}
PATIENT_COUNT=${PATIENT_COUNT:-100}
WORK_DIR="/tmp/synthetic-${PIPELINE_RUN_ID}"
FHIR_DIR="${WORK_DIR}/fhir"
OMOP_DIR="${WORK_DIR}/omop"

# Create working directories
mkdir -p "${FHIR_DIR}" "${OMOP_DIR}"

echo "Step 1: Generating ${PATIENT_COUNT} synthetic patients..."
python /app/synthetic/generators/unified_generator.py \
  --count "${PATIENT_COUNT}" \
  --fhir-dir "${FHIR_DIR}" \
  --omop-dir "${OMOP_DIR}" \
  --seed 42

echo "Step 2: Flattening FHIR to Parquet..."
python /app/synthetic/etl/flatten_fhir.py \
  --input-dir "${FHIR_DIR}" \
  --output-file "${FHIR_DIR}/fhir_patient_flat.parquet" \
  --bundle

echo "Step 3: Validating cross-model consistency..."
python /app/synthetic/scripts/validate_cross_model.py \
  --omop-dir "${OMOP_DIR}" \
  --fhir-dir "${FHIR_DIR}"

# Upload to S3 if bucket is configured
if [ -n "${S3_DATA_BUCKET:-}" ]; then
  S3_PREFIX="s3://${S3_DATA_BUCKET}/runs/${PIPELINE_RUN_ID}"
  
  echo "Step 4: Uploading to S3: ${S3_PREFIX}"
  
  # Upload FHIR data
  aws s3 cp "${FHIR_DIR}/patients_bundle.json" "${S3_PREFIX}/fhir/patients_bundle.json"
  aws s3 cp "${FHIR_DIR}/fhir_patient_flat.parquet" "${S3_PREFIX}/fhir/fhir_patient_flat.parquet"
  
  # Upload OMOP data
  aws s3 sync "${OMOP_DIR}/" "${S3_PREFIX}/omop/" --exclude "*" --include "*.parquet"
  
  echo "✓ Data uploaded to ${S3_PREFIX}"
else
  echo "⚠ S3_DATA_BUCKET not set, skipping upload"
  echo "✓ Data available locally at ${WORK_DIR}"
fi

echo "=== Pipeline Complete ==="
