# Pipeline SLO / SLA Definitions

## 1. Overview
Defines expected operational performance for the synthetic → ETL → dbt pipeline.

## 2. Service Level Objectives (SLO)

### SLO 1 — Pipeline Success Rate
- **Target:** 99% successful runs per month  
- **Measure:** Step Functions execution status

### SLO 2 — Pipeline Completion Time
- **Target:** < 20 minutes for full pipeline  
- **Measure:** execution duration

### SLO 3 — Data Quality Tests
- **Target:** 100% dbt schema tests passing  
- **Measure:** dbt test output

### SLO 4 — Data Freshness
- **Target:** Synthetic data regenerated at least weekly  
- **Measure:** Max ingestion timestamp in Iceberg tables

## 3. SLAs (optional)
Internal-only, non-customer facing:
- Investigation of pipeline failures within 24 hours  
- Fixes for critical issues within 48 hours  

## 4. Error Budget
- Monthly failure tolerance: 0.5% of pipeline runs  
