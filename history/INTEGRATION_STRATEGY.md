# Integration Strategy: Synthetic Healthlake + 4-Week Platform Plan

## Executive Summary
This document outlines the strategy to merge the existing **Synthetic Healthlake** reference architecture (focus on generation & validation) with the new **4-Week Plan** (focus on Data Platform, Snowflake, & API access).

**Core Concept**: Treat the existing `synthetic/` module as the **Upstream Data Producer** that feeds the new **Downstream Platform** (Lambda -> Snowflake -> API).

---

## 1. Architectural Alignment

| Component | Existing (`synthetic-healthlake`) | New (4-Week Plan) | Integration Strategy |
|-----------|-----------------------------------|-------------------|----------------------|
| **Data Source** | Custom Python Generator (Parquet/FHIR) | "Synthea data" | **Use Existing**. The `synthetic/` generator is superior to raw Synthea as it produces correlated FHIR+OMOP. We will configure it to output NDJSON for the new pipeline. |
| **Ingestion** | Step Functions -> Fargate -> S3 | S3 Event -> Lambda | **Adopt New**. Replace the heavy Fargate/Step Functions generation pipeline with a lighter trigger or just use the generator CLI to drop files into the landing bucket that triggers the NEW Lambda pipeline. |
| **Storage** | Iceberg + Athena | Snowflake | **Migrate**. Shift the "Gold" layer to Snowflake. The existing Iceberg setup can remain as a "Data Lake" reference, but the primary roadmap will focus on Snowflake tables. |
| **Transformation**| dbt (Athena/DuckDB) | dbt (Snowflake) | **Port**. Create a new `dbt/snowflake` project. Port the logic from `dbt/fhir_omop_dbt` but adapt DDLs for Snowflake. |
| **API Layer** | None (Direct SQL) | AWS Lambda + API Gateway | **New Build**. This is net-new functionality (Weeks 3-4). |

---

## 2. Directory Structure Plan

We will reorganize the repository to separate the "Generator" (Tooling) from the "Platform" (Infrastructure).

```text
synthetic-healthlake/
├── synthetic/                  # [KEEP] Existing data generation library
│   ├── generators/
│   └── ...
├── platform/                   # [NEW] The "4-Week Plan" implementation
│   ├── ingestion/              # Week 1: Lambdas for ingestion
│   ├── api/                    # Week 3-4: API Lambdas
│   └── infrastructure/         # Terraform/SAM templates
├── dbt/                        # [REFINE]
│   ├── snowflake/              # [NEW] Week 2: New dbt project
│   └── legacy_athena/          # [MOVE] Old dbt project
├── tests/                      # [MERGE] Unified tests
└── docs/                       # [UPDATE]
```

---

## 3. Work Breakdown (Agent Sessions)

To achieve the 4-week plan, we break the work into 4 "Agent Sessions" (approx 2-3 days of work each).

### Session 1: Ingestion Pipeline (Week 1)
**Goal**: Get data from `synthetic` generator into S3 and trigger generic processing.
- [ ] Refactor `synthetic` to output NDJSON (if not already supported).
- [ ] Implement `platform/ingestion` Lambdas (`fhir_parser`, `loader`).
- [ ] Set up S3 Event Notifications.
- [ ] Verify: Run generator -> File lands in S3 -> Lambda triggers -> Parsed JSON in target bucket.

### Session 2: Data Warehousing (Week 2)
**Goal**: Ingest data into Snowflake and transform it.
- [ ] Configure Snowflake free tier (User action required).
- [ ] Implement Snowpipe for auto-ingestion.
- [ ] Initialize `dbt/snowflake`.
- [ ] Port `stg_patient` and `stg_encounter` models to Snowflake SQL.
- [ ] Verify: S3 data appears in Snowflake tables automatically.

### Session 3: API Foundation (Week 3)
**Goal**: Read-only access to Patient data.
- [ ] Implement `platform/api/authorizer` (Lambda Authorizer).
- [ ] Implement `platform/api/patient` (GET/Search).
- [ ] Connect Lambda to Snowflake.
- [ ] Verify: `curl` request returns JSON patient data from Snowflake.

### Session 4: Expansion & Polish (Week 4)
**Goal**: Full resource support and production readiness.
- [ ] Add Encounter/Observation endpoints.
- [ ] Add Ingestion API (webhook).
- [ ] Finalize Documentation & OpenAPI spec.

---

## 4. Immediate Next Steps
1.  **Approval**: Confirm this strategy.
2.  **Repo Prep**: Create the new folder structure.
3.  **Start Session 1**: Begin implementing the Ingestion Lambdas.
