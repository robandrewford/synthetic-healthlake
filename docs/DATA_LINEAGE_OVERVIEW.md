# Data Lineage Overview

## 1. Purpose
Provide end-to-end traceability for synthetic data through:
- Generation
- Validation
- Flattening (FHIR/OMOP → Parquet)
- Modeling (dbt)
- Analytics (Athena)

## 2. Lineage Strategy
### Ingestion Timestamps
Each record contains:
- `omop_ingestion_ts`
- `fhir_ingestion_ts`
- Computed fields:
  - `lineage_first_seen_ts`
  - `lineage_last_updated_ts`
  - `lineage_sources`

### Synthetic Source Tracking
- `synthetic_source` field indicates generator and version  
- Helps track changes across generation runs  

### Pipeline Run Tracking
- Optional `pipeline_run_id` macro argument in dbt  
- Enables tracing records to pipeline execution  

## 3. dbt Integration
Lineage included via:
- `lineage_standard_columns` macro
- Applied across staging + marts

## 4. Iceberg Time Travel
- Supports rollback and historical analysis  
- Aligns with lineage timestamps  

## 5. Visualization
For full observability, integrate with:
- OpenLineage  
- Marquez  
- or custom dashboards using Athena views  

