# Metrics Layer Overview

The metrics layer defines reusable metrics on top of harmonized FHIR + OMOP semantic models.  
It supports Athena, dbt, and downstream reporting tools (QuickSight, Mode, Superset).

---

## 1. Purpose
- Provide consistent, validated healthcare metrics.
- Standardize chronic-condition indicators across OMOP + FHIR.
- Enable rapid iteration on early-stage analytics and ML experiments.

---

## 2. Location

The metrics layer is defined in the `dbt/fhir_omop_dbt/models/metrics` directory.
dbt/fhir_omop_dbt/models/metrics/metrics_chronic_condition.yml
---

## 3. Key Metrics

### 3.1 chronic_condition_count
Counts chronic conditions per patient.

**Definition:**
- Derived from `fact_chronic_condition`
- Groups by `person_id` / `patient_id`
- Filters by curated condition concept set

### 3.2 condition_prevalence_rate
prevalence = chronic_condition_count / total_patients

Useful for:
- Longitudinal cohort analytics
- Measuring disease burden in synthetic populations

### 3.3 age_at_first_condition
From `dim_patient` + `fact_chronic_condition`.

---

## 4. Example dbt Metric Block

```yaml
metrics:
  - name: chronic_condition_count
    model: ref('fact_chronic_condition')
    label: "Chronic Condition Count"
    type: count
    sql: condition_concept_id
    timestamp: condition_start_datetime
    filters:
      - field: is_chronic
        operator: "="
        value: "true"
```

### 5. Usage in Queries

```sql
select *
from {{ metrics.calculate(metric('chronic_condition_count')) }}
order by chronic_condition_count desc;
```

### 6. Roadmap

- Add comorbidity indices (Charlson, Elixhauser)
- Add risk-adjusted synthetic indicators
- Add visit frequency metrics per specialty
