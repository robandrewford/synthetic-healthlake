# Step 1: Generate Synthea Data

## Overview

Generate synthetic FHIR patient data using Synthea for local development and testing of the Lambda pipeline.

---

## Local Setup

```bash
# Clone Synthea
git clone https://github.com/synthetichealth/synthea.git
cd synthea

# Build (requires Java 11+)
./gradlew build check

# Generate 1000 patients with chronic conditions relevant to healthtech
./run_synthea \
  --exporter.fhir.export true \
  --exporter.fhir.bulk_data true \
  --exporter.baseDirectory ./output \
  --generate.demographics.default_file ./src/main/resources/geography/demographics.csv \
  -p 1000 \
  -m diabetes \
  -m heart_failure \
  -m obesity
```

---

## Output Structure

```
output/fhir/
├── hospitalInformation1234.json      # Organization bundles
├── practitionerInformation1234.json  # Practitioner bundles
├── Abby_Smith_12345.json             # Patient bundles (one per patient)
├── ...
```

---

## Upload to S3 Source Bucket

```bash
# Create source bucket (simulates Epic's export endpoint)
aws s3 mb s3://healthtech-fhir-source

# Upload Synthea output
aws s3 sync output/fhir/ s3://healthtech-fhir-source/synthea/batch-001/
```

---

## Verification

```bash
# Verify upload
aws s3 ls s3://healthtech-fhir-source/synthea/batch-001/ --summarize

# Check file count
aws s3 ls s3://healthtech-fhir-source/synthea/batch-001/ | wc -l
```
