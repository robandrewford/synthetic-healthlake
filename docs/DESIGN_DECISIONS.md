# Design Decisions

This document captures major architectural and design decisions for the FHIR-OMOP Synthetic Stack.

## 1. Use of AWS Iceberg on S3
### Decision
Use Apache Iceberg tables stored in S3 with Glue Catalog.
### Rationale
- ACID guarantees
- Time Travel
- Compatible with Athena & dbt
- Works well with synthetic data versioning

## 2. ECS Fargate for Compute
### Decision
Run synthetic generators, ETL, and dbt processing as Fargate tasks.
### Rationale
- Serverless batch compute
- Minimal ops overhead
- Runs securely in private subnets

## 3. dbt for Semantic Modeling
### Decision
Use dbt for all staging, dimensional, and fact modeling.
### Rationale
- Works well with SQL-based transformations
- Built-in testing, documentation, governance
- Rapid iteration for early-stage analytics

## 4. Step Functions for Orchestration
### Decision
A pipeline chain: synthetic → FHIR pipes → OMOP parquet → dbt.
### Rationale
- Declarative pipeline state machine
- Retry logic and error reporting
- Clear separation of responsibilities

## 5. Synthetic-First Architecture
### Decision
All data is synthetic-only; no PHI/PII allowed.
### Rationale
- Safe for local and cloud development
- Enables realistic analytics without risking compliance issues

## 6. Terminology and Constraints Layer
### Decision
Use YAML configs for domain logic, constraints, and distributions.
### Rationale
- Human-readable
- Easy to version-control
- Extensible for clinical logic

## 7. Future: Lake Formation Hardening
### Decision
Move toward Lake Formation for fine-grained access control.
### Rationale
- Column-level permissions
- Auditable and centralized governance
