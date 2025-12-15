# Metrics Layer Overview

The metrics layer defines reusable metrics on top of harmonized FHIR + OMOP semantic models.
It supports Athena, dbt, and downstream BI tools.

## 1. Purpose
- Provide consistent healthcare metrics.
- Standardize chronic-condition indicators across OMOP + FHIR.
- Accelerate analytics and ML experiments on synthetic data.

## 2. Location
- dbt metrics config: `dbt/fhir_omop_dbt/models/metrics/metrics_chronic_condition.yml`

## 3. Key Metrics (Conceptual)

- **patient_count**: distinct patients from `dim_patient`.
- **chronic_condition_patient_count**: distinct patients with chronic conditions from `fact_chronic_condition`.
- **chronic_condition_prevalence**: ratio of condition patients to total patients.
- **chronic_condition_diagnosis_rate**: average diagnosis count per condition patient.

## 4. Example Usage Pattern (Conceptual)

```sql
-- Example: prevalence of DM2 by gender
select
  gender,
  metric(chronic_condition_prevalence) as dm2_prevalence
from metrics
where chronic_condition_code = 'DM2'
group by gender;
```

## 5. Roadmap
- Add comorbidity indices (Charlson, Elixhauser).
- Add visit-frequency and utilization metrics.
- Add time-to-diagnosis and disease progression metrics.
