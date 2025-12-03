#!/bin/bash
set -euo pipefail

# Pipeline Smoke Test - Runs minimal end-to-end pipeline locally

echo "=== Pipeline Smoke Test ==="

# Set test parameters
export PIPELINE_RUN_ID="smoke-test-$(date +%Y%m%d-%H%M%S)"
export PATIENT_COUNT=10
WORK_DIR="/tmp/smoke-test-${PIPELINE_RUN_ID}"

echo "Test ID: ${PIPELINE_RUN_ID}"
echo "Work directory: ${WORK_DIR}"

# Clean up previous test
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

echo ""
echo "Step 1: Generate 10 synthetic patients..."
uv run python synthetic/generators/unified_generator.py \
  --count 10 \
  --fhir-dir "${WORK_DIR}/fhir" \
  --omop-dir "${WORK_DIR}/omop" \
  --seed 42

echo ""
echo "Step 2: Flatten FHIR to Parquet..."
uv run python synthetic/etl/flatten_fhir.py \
  --input-dir "${WORK_DIR}/fhir" \
  --output-file "${WORK_DIR}/fhir/fhir_patient_flat.parquet" \
  --bundle

echo ""
echo "Step 3: Validate cross-model consistency..."
uv run python synthetic/scripts/validate_cross_model.py \
  --omop-dir "${WORK_DIR}/omop" \
  --fhir-dir "${WORK_DIR}/fhir"

echo ""
echo "Step 4: Verify output files..."
EXPECTED_FILES=(
  "${WORK_DIR}/fhir/patients_bundle.json"
  "${WORK_DIR}/fhir/fhir_patient_flat.parquet"
  "${WORK_DIR}/omop/person.parquet"
  "${WORK_DIR}/omop/condition_occurrence.parquet"
  "${WORK_DIR}/omop/measurement.parquet"
)

ALL_EXIST=true
for file in "${EXPECTED_FILES[@]}"; do
  if [ -f "$file" ]; then
    SIZE=$(du -h "$file" | cut -f1)
    echo "  ✓ $file ($SIZE)"
  else
    echo "  ✗ Missing: $file"
    ALL_EXIST=false
  fi
done

echo ""
if [ "$ALL_EXIST" = true ]; then
  echo "=== ✓ Smoke Test PASSED ==="
  echo "All files generated successfully"
  echo "Test data available at: ${WORK_DIR}"
  exit 0
else
  echo "=== ✗ Smoke Test FAILED ==="
  echo "Some expected files were not generated"
  exit 1
fi
