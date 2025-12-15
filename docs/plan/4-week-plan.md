# Extended 4-Week Plan: Healthtech Data Platform + API Layer

## Overview

AWS-native architecture with Lambda learning path, Synthea synthetic FHIR data, and Bezos Mandate-compliant API layer.

**Stack**: AWS Lambda + Step Functions + API Gateway + S3 + Snowflake + dbt Core + GitHub Actions

**Team**: 2 Data Engineers

**Constraint**: Zero SaaS orchestration cost; all data access via service interfaces

---

## Week 1: Lambda Pipeline & Infrastructure

| Day | Action | Deliverable | Owner |
|-----|--------|-------------|-------|
| 1 | Install SAM CLI; scaffold Lambda project structure | `lambda_functions/` skeleton | DE1 |
| 1 | Generate Synthea data (1000 patients with diabetes, heart failure, obesity); upload to S3 | `s3://healthtech-fhir-source/synthea/batch-001/` | DE2 |
| 2 | Implement `fhir_parser.py` with unit tests | Parser module with pytest coverage | DE1 |
| 2 | Implement `initiate_export.py` with moto tests | Lambda 1 tested locally | DE1 |
| 3 | Implement `poll_export_status.py` | Lambda 2 tested locally | DE1 |
| 3 | Implement `download_resources.py` | Lambda 3 tested locally | DE1 |
| 4 | Create SAM template; deploy to dev | Lambdas deployed to AWS | DE1 |
| 4 | Create Step Functions state machine | `fhir-ingestion-dev` state machine deployed | DE2 |
| 5 | End-to-end test: manual execution, verify S3 output | Pipeline producing NDJSON in `landing/fhir/` | Both |

### Week 1 Deliverables

- [ ] 3 Lambda functions deployed and tested
- [ ] Step Functions state machine orchestrating Lambdas
- [ ] Synthea FHIR data transformed to NDJSON in S3 landing zone
- [ ] CloudWatch logs configured for all Lambdas

---

## Week 2: dbt + Snowflake + CI/CD

| Day | Action | Deliverable | Owner |
|-----|--------|-------------|-------|
| 1 | Initialize dbt project with three-zone structure | `dbt/` with `staging/vault/`, `intermediate/`, `marts/` | DE1 |
| 1 | Configure Snowpipe for NDJSON auto-ingestion | S3 event → Snowflake `RAW.FHIR_*` tables | DE2 |
| 2 | First staging model: `stg_vault__patient.sql` | FHIR JSON parsed to relational columns | DE1 |
| 2 | Add dbt tests for Patient model (`not_null`, `unique`, schema) | `_stg_vault__models.yml` with tests | DE1 |
| 3 | Staging models: Encounter, Observation, Condition | Core FHIR resources modeled | DE1 |
| 3 | Intermediate layer: tokenization model | `_int_tokenize_patient.sql` applying deterministic tokens | DE2 |
| 4 | GitHub Actions CI: SQLFluff lint + dbt test on PR | `.github/workflows/dbt_ci.yml` | DE2 |
| 4 | Terraform: ECS Fargate task definition for dbt runner | `terraform/ecs.tf` with dbt container | DE2 |
| 5 | Integration test: full pipeline S3 → Snowpipe → Snowflake → dbt | End-to-end data flow verified | Both |

### Week 2 Deliverables

- [ ] dbt project with staging models for Patient, Encounter, Observation, Condition
- [ ] Tokenization boundary implemented in intermediate layer
- [ ] Snowpipe auto-ingesting NDJSON from S3
- [ ] GitHub Actions CI running on pull requests
- [ ] ECS task definition ready for dbt execution

---

## Week 3: API Layer Foundation (Bezos Mandate)

| Day | Action | Deliverable | Owner |
|-----|--------|-------------|-------|
| 1 | Scaffold API Lambda project structure | `api_authorizer/`, `fhir_api/`, `ingestion_api/`, `shared/` | DE1 |
| 1 | Implement `shared/organization.py` (org-scoped queries) | Security boundary enforced | DE1 |
| 2 | Implement `api_authorizer` Lambda (JWT validation) | Token validation with JWKS | DE2 |
| 2 | Implement `fhir_api/snowflake_client.py` | Connection pooling + org scoping | DE1 |
| 3 | Implement `fhir_api/patient.py` (GET, Search) | `/v1/fhir/Patient` endpoints | DE1 |
| 3 | Implement `fhir_api/handler.py` (router) | API Gateway proxy handler | DE1 |
| 4 | Snowflake RBAC: create `API_READER` role | Least-privilege access configured | DE2 |
| 4 | Create `template-api.yaml` SAM template | API Gateway + Lambda + WAF | DE2 |
| 5 | Deploy API Gateway to dev; manual testing | Secured `/v1/fhir/Patient` working | Both |

### Week 3 Deliverables

- [ ] Lambda Authorizer validating JWT tokens
- [ ] Organization-scoped data access enforced at query layer
- [ ] Patient GET and Search endpoints functional
- [ ] API Gateway with WAF deployed
- [ ] Snowflake `API_READER` role with analytics-only access

---

## Week 4: API Expansion + Integration Testing

| Day | Action | Deliverable | Owner |
|-----|--------|-------------|-------|
| 1 | Implement `fhir_api/encounter.py` | `/v1/fhir/Encounter` endpoints | DE1 |
| 1 | Implement `fhir_api/observation.py` | `/v1/fhir/Observation` endpoints | DE1 |
| 2 | Implement `ingestion_api/handler.py` (webhook receiver) | `/v1/ingestion/fhir/Bundle` POST | DE2 |
| 2 | Implement `ingestion_api/presigned_url.py` | `/v1/ingestion/upload-url` endpoint | DE2 |
| 3 | Create dbt models for API consumption | `marts/api/dim_patient_api.sql` with contracts | DE1 |
| 3 | Integration test: API → Snowflake → verify org isolation | Cross-org access blocked | DE2 |
| 4 | Load testing with sample organization data | Baseline performance metrics | Both |
| 4 | API documentation (OpenAPI spec) | `openapi.yaml` for developer portal | DE2 |
| 5 | Security review: token validation, RBAC, audit logs | Compliance checklist complete | Both |

### Week 4 Deliverables

- [ ] Full FHIR API: Patient, Encounter, Observation
- [ ] Ingestion API: webhook + presigned URL upload
- [ ] dbt models with enforced contracts for API layer
- [ ] Organization isolation verified via integration tests
- [ ] OpenAPI specification for external developers
- [ ] Bezos Mandate compliance checklist signed off

---

## Bezos Mandate Compliance Checklist

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| All data via service interfaces | API Gateway + Lambda for all external access | ☐ |
| No direct database reads | API_READER role has no vault access | ☐ |
| No shared memory | Stateless Lambda functions | ☐ |
| Network calls only | All inter-service via HTTPS (API Gateway, SQS) | ☐ |
| Externalizable from day 1 | Same API for internal and external consumers | ☐ |
| Organization isolation | Mandatory `organization_id` in every query | ☐ |

---

## Service Interface Contracts Summary

### Ingestion Service (`/v1/ingestion`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/ingestion/fhir/Bundle` | POST | Receive FHIR Bundle |
| `/v1/ingestion/upload-url` | POST | Get presigned S3 URL |
| `/v1/ingestion/jobs/{jobId}` | GET | Poll job status |

### Data Access Service (`/v1/fhir`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/fhir/Patient/{id}` | GET | Get patient by ID |
| `/v1/fhir/Patient` | GET | Search patients |
| `/v1/fhir/Encounter/{id}` | GET | Get encounter |
| `/v1/fhir/Observation` | GET | Search observations |

### Export Service (`/v1/export`) — Future

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/export/$export` | POST | Initiate bulk export |
| `/v1/export/jobs/{jobId}` | GET | Poll export status |

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| JWT/OAuth complexity | Medium | Use managed identity provider (Auth0/Cognito) |
| Snowflake cold start latency | Medium | Keep-warm queries; consider caching layer |
| API rate limiting tuning | Medium | Start conservative; adjust based on load testing |
| Cross-org data leak | Low | Defense in depth: authorizer + query filter + RBAC |
| Two-engineer bandwidth | High | Strict scope; defer Export Service to Week 5+ |

---

## Deferred to Week 5+

- Export Service (`/v1/export`) for bulk FHIR export
- Analytics endpoints (`/v1/analytics/cohort`, `/v1/analytics/metrics`)
- Developer portal with API key management
- Custom domain + TLS certificate for API Gateway
- ElastiCache for frequently-accessed patient data
- Epic Bulk FHIR integration (replace Synthea with real endpoint)
