# Data Quality Strategy

## 1. Objectives
Ensure high-quality synthetic datasets across FHIR and OMOP to support analytics, AI/ML pipelines, and compliance prototyping.

## 2. Quality Dimensions
- **Completeness**: Required fields populated per FHIR/OMOP spec.
- **Validity**: Values respect terminology, domain constraints, and distributions.
- **Consistency**: OMOP + FHIR representations harmonized.
- **Timeliness**: Lineage timestamps reflect refresh cycles.
- **Accuracy**: Clinical logic approximated within synthetic bounds.

## 3. Controls
### Schema Checks
- dbt tests for not-null, unique, accepted values.

### Domain Logic
- YAML-based constraints:
  - Age ranges
  - Gender mappings
  - Condition concept validity

### Referential Integrity
- Patient/Visit/Condition/Measurement joins validated with dbt tests.

### Synthetic Validity Checks
- “Cross-model validation” compares FHIR Patient and OMOP Person.

## 4. Monitoring
- dbt test results stored per-run.
- Pipeline alerts on failures.
- BI dashboards to track quality metrics.

