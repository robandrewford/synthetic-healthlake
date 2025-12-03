# Data Governance Plan

## 1. Governance Objectives
- Ensure only **synthetic data** is processed.
- Maintain transparent lineage across FHIR + OMOP.
- Enforce schema, terminology, and semantic consistency.
- Enable auditability and reproducibility.

## 2. Data Classification
All project data is classified as:
- **Synthetic Clinical Data**: Non-PII, non-PHI, not derived from real patients.

## 3. Data Lifecycle
1. **Generation** — Synthetic datasets created using rules and mappings.
2. **Validation** — Cross-model consistency checks.
3. **Ingestion** — Stored as raw and flattened datasets.
4. **Modeling** — Transformed by dbt into analytics layers.
5. **Consumption** — Queried by Athena or exported for ML.

## 4. Access Controls
- IAM roles define all S3, Glue, and Athena access.
- Future: Lake Formation fine-grained governance (tables/columns).
- No public access allowed.

## 5. Quality Controls
- dbt tests ensure schema and referential integrity.
- Lineage macro tracks ingestion timestamps and sources.
- Synthetic validation enforces clinical and semantic rules.

## 6. Compliance
- Architecture avoids PHI/PII and aligns with:
  - HIPAA (no PHI processed)
  - SOC2 Security, Availability principles
  - Internal data governance standards

## 7. Monitoring
- CloudWatch for logs and metrics.
- Athena usage logs for query audits.
- Step Functions logs pipeline outcomes.

