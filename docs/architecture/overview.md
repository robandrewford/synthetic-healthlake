# Architecture Overview

## 1. Purpose
This document summarizes the end-to-end architecture for the FHIR-OMOP Synthetic Stack, including storage, compute, orchestration, and modeling layers.

## 2. High-Level Architecture Components
- **Synthetic Data Layer**  
  Generates OMOP and FHIR synthetic datasets using domain logic, terminology, and validation.

- **Ingestion + Flattening**  
  Converts synthetic raw data into Iceberg-compatible Parquet (FHIR Data Pipes + OMOP converters).

- **Lakehouse Storage**
  - Apache Iceberg tables on AWS S3
  - Glue Catalog as metastore
  - Athena for interactive SQL

- **Transformation Layer**
  - dbt for staging, dimensional models, facts, and metrics
  - dbt tests ensure schema and relationship quality

- **Compute Layer**
  - ECS Fargate for batch jobs
  - API service for optional external interactions

- **Orchestration**
  - AWS Step Functions pipeline:
    ```
    synthetic → fhir-pipes → omop-parquet → dbt
    ```

- **Security & Governance**
  - IAM least privilege
  - VPC private subnets & endpoints
  - KMS encryption for all data
  - Optional Lake Formation

## 3. Data Flow
1. Synthetic generators write raw data to S3.
2. ETL jobs flatten and standardize into Iceberg tables.
3. dbt builds analytics-ready models.
4. Athena queries models for analytics and ML.

## 4. Diagram
Architecture diagrams are located in `docs/diagrams/`.
