# FHIR-OMOP Synthetic Stack — Documentation Index

## 1. Introduction
- [README](../README.md)
- [ARCHITECTURE_OVERVIEW](ARCHITECTURE_OVERVIEW.md)
- [DESIGN_DECISIONS](DESIGN_DECISIONS.md)

## 2. Governance
- [GOVERNANCE](GOVERNANCE.md)
- [SECURITY](SECURITY.md)
- [DATA_GOVERNANCE_PLAN](DATA_GOVERNANCE_PLAN.md)
- [ACCESS_CONTROL_MATRIX](ACCESS_CONTROL_MATRIX.md)
- [RISK_REGISTER](RISK_REGISTER.md)
- [THREAT_MODEL](THREAT_MODEL.md)

## 3. Architecture & Operations
- [OBSERVABILITY_PLAN](OBSERVABILITY_PLAN.md)
- [COST_MANAGEMENT_STRATEGY](COST_MANAGEMENT_STRATEGY.md)
- [PIPELINE_SLO_SLA](PIPELINE_SLO_SLA.md)
- [OPERATIONS](OPERATIONS.md)

## 4. Data & Modeling
- [DATA_QUALITY_STRATEGY](DATA_QUALITY_STRATEGY.md)
- [DATA_LINEAGE_OVERVIEW](DATA_LINEAGE_OVERVIEW.md)
- [VALIDATION_FRAMEWORK](VALIDATION_FRAMEWORK.md)

## 5. Synthetic Data Layer
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

## 6. dbt Project
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

## 7. Iceberg Schema Layer
- Iceberg DDLs  
  - `iceberg-ddl/person_iceberg.sql`  
  - `iceberg-ddl/fhir_patient_flat_iceberg.sql`  
  - `iceberg-ddl/visit_occurrence_iceberg.sql`  
  - `iceberg-ddl/condition_occurrence_iceberg.sql`  
  - `iceberg-ddl/measurement_iceberg.sql`  
  - `iceberg-ddl/fhir_encounter_flat_iceberg.sql`

## 8. Infrastructure as Code
- CDK Project  
  - `cdk/bin/app.ts`  
  - `cdk/lib/fhir-omop-stack.ts`  
  - `cdk/tsconfig.json`  
  - `cdk/package.json`

## 9. CI/CD Automation
- GitHub Actions Workflows  
  - `.github/workflows/cdk-deploy.yml`  
  - `.github/workflows/dbt-tests.yml`  
  - `.github/workflows/synthetic-smoke.yml`

## 10. API Layer
- [API_SPECIFICATION](API_SPECIFICATION.md)

## 11. Release Engineering
- [RELEASE](RELEASE.md)
- [CHANGELOG](CHANGELOG.md)
- [CODING_STANDARDS](CODING_STANDARDS.md)
- [CONTRIBUTING](CONTRIBUTING.md)
