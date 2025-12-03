# Validation Framework

## 1. Purpose
Ensure all synthetic FHIR + OMOP data adheres to clinical-semantic rules, model integrity, and expected statistical properties.

## 2. Validation Layers

### Layer 1 — Schema Validation
- Validate parquet structure against iceberg-ddl definitions
- dbt schema tests: not-null, unique, accepted values

### Layer 2 — Domain Logic
- YAML-defined constraints:
  - Age ranges
  - Codesets
  - Demographic distributions

### Layer 3 — Semantic Validation
- Cross-model validation:
  - FHIR patient <-> OMOP person linkage
  - Encounter consistency

### Layer 4 — Statistical Validation
- Validate distributions match expectations
- Check anomalies (e.g. too many centenarians)

### Layer 5 — Pipeline Validation
- Step Functions success states
- ECS task exit codes
- Log-based anomaly detection

## 3. Validation Tools
- Python validation scripts
- dbt tests
- Athena anomaly queries

## 4. Reports
- Generate validation reports per-run  
- Store summaries in S3 for audit and reproducibility  
