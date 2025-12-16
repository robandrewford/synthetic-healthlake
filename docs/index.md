# FHIR-OMOP Synthetic Stack — Documentation Index

## 1. Introduction
- [README](../README.md)
- [Architecture Overview](architecture/overview.md)
- [Design Decisions](architecture/design-decisions.md)

## 2. Architecture
- [Overview](architecture/overview.md)
- [Design Decisions](architecture/design-decisions.md)
- [Diagrams](diagrams/)

## 3. Governance & Security
- [Governance](governance/governance.md)
- [Data Governance Plan](governance/data-governance-plan.md)
- [Access Control Matrix](governance/access-control-matrix.md)
- [Risk Register](governance/risk-register.md)
- [Threat Model](governance/threat-model.md)
- [Security Policy](security/security.md)
- [Security Checklist](security/security-checklist.md)
- [Deployment Checklist](security/deployment-checklist.md)
- [Secrets Management](security/secrets-management.md)
- [Dependency Scanning](security/dependency-scanning.md)

## 4. Operations

- [Operations Guide](operations/operations.md)
- [Observability Plan](operations/observability-plan.md)
- [Cost Management Strategy](operations/cost-management-strategy.md)
- [Pipeline SLO/SLA](operations/pipeline-slo-sla.md)

## 5. Data Management
- [Data Quality Strategy](data/data-quality-strategy.md)
- [Data Lineage Overview](data/data-lineage-overview.md)
- [Validation Framework](data/validation-framework.md)

## 6. Technical Reference
- [API Specification](reference/api-specification.md)
- [Iceberg DDL](reference/iceberg-ddl.md)
- [Lineage Macro](reference/lineage-macro.md)
- [Metrics Layer](reference/metrics-layer.md)

## 7. Synthetic Data Layer
- Synthetic Configurations
  - `synthetic/config/domain_constraints.yaml`
  - `synthetic/config/terminology_mappings.yaml`
  - `synthetic/config/distribution_profiles.yaml`
- Synthetic Pipeline Scripts
  - `synthetic/scripts/generate_fhir.py`
  - `synthetic/scripts/generate_omop.py`
  - `synthetic/scripts/apply_domain_constraints.py`
  - `synthetic/scripts/validate_cross_model.py`
- [Synthetic Pipeline Makefile](../synthetic/Makefile)

## 8. dbt Project
- Sources (`models/sources/sources_fhir_omop.yml`)
- Staging Models
  - `models/staging/stg_person.sql`
  - `models/staging/stg_fhir_patient.sql`
- Marts
  - `models/marts/dim_patient.sql`
  - `models/marts/fact_chronic_condition.sql`
- Metrics Layer
  - `models/metrics/metrics_chronic_condition.yml`
- Macros
  - `macros/lineage.sql`

## 9. Iceberg Schema Layer
- Iceberg DDLs
  - `iceberg-ddl/person_iceberg.sql`
  - `iceberg-ddl/fhir_patient_flat_iceberg.sql`
  - `iceberg-ddl/visit_occurrence_iceberg.sql`
  - `iceberg-ddl/condition_occurrence_iceberg.sql`
  - `iceberg-ddl/measurement_iceberg.sql`
  - `iceberg-ddl/fhir_encounter_flat_iceberg.sql`

## 10. Infrastructure as Code
- CDK Project
  - `cdk/bin/app.ts`
  - `cdk/lib/fhir-omop-stack.ts`
  - `cdk/tsconfig.json`
  - `cdk/package.json`

## 11. CI/CD Automation
- GitHub Actions Workflows
  - `.github/workflows/cdk-deploy.yml`
  - `.github/workflows/dbt-tests.yml`
  - `.github/workflows/synthetic-smoke.yml`

## 12. Development
- [Contributing](development/contributing.md)
- [Coding Standards](development/coding-standards.md)
- [Release Process](development/release.md)
- [Changelog](development/changelog.md)
