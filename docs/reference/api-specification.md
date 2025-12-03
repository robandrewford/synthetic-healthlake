# API Specification

## 1. Overview
Optional API service running as ECS Fargate microservice behind ALB.  
Provides metadata, pipeline triggers, and retrieval of synthetic run summaries.

## 2. Base URL
```
https://<api-endpoint>/
```

## 3. Endpoints

### GET /health
**Description:** Health check  
**Response:** `{ "status": "ok" }`

### POST /pipeline/run
**Description:** Trigger a Step Functions execution  
**Body:**  
```
{
  "run_type": "full|synthetic_only|dbt_only"
}
```

### GET /pipeline/runs/{id}
**Description:** Fetch metadata about a pipeline execution.

### GET /datasets/{dataset_name}
**Description:** List available synthetic datasets.  
**Examples:** `omop_raw`, `fhir_raw`, `iceberg_tables`

### GET /datasets/{dataset_name}/schema
Returns the Glue table schema.

## 4. Security
- IAM-based auth or Cognito access token
- TLS-only
