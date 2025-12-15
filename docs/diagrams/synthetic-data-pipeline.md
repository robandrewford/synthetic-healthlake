# Synthetic Data Pipeline

The synthetic data pipeline produces harmonized OMOP + FHIR synthetic datasets using domain rules,
terminology mappings, and statistical distributions.

## 1. Goals
- Generate realistic but non-identifiable clinical data.
- Validate FHIR ↔ OMOP joins and analytics models.
- Provide reusable synthetic cohorts for ML and dashboard prototyping.

## 2. Layout

```text
synthetic/
  Makefile
  config/
    domain_constraints.yaml
    terminology_mappings.yaml
    distribution_profiles.yaml
  scripts/
    generate_fhir.py
    generate_omop.py
    apply_domain_constraints.py
    validate_cross_model.py
```

## 3. Stages

1. **OMOP Generation (`generate_omop.py`)**
   - Produces OMOP tables (person, visit_occurrence, condition_occurrence, measurement).
2. **FHIR Generation (`generate_fhir.py`)**
   - Produces FHIR Patient / Encounter / Condition / Observation, linked to OMOP ids.
3. **Domain Constraints (`apply_domain_constraints.py`)**
   - Enforces clinical rules, terminology, and distribution profiles.
4. **Cross-Model Validation (`validate_cross_model.py`)**
   - Ensures OMOP and FHIR representations are consistent.

## 4. Local Run

```bash
make -C synthetic all
```

Outputs synthetic data into raw directories (or S3 when containerized).

## 5. Orchestration on AWS

In the full architecture, each stage is an ECS Fargate task and the sequence:

```text
synthetic → fhir-pipes → omop-parquet → dbt
```

is orchestrated by AWS Step Functions.
