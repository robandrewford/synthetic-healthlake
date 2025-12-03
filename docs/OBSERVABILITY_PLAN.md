# Observability Plan

## 1. Goals
- Ensure visibility into pipeline execution
- Track data quality and lineage
- Support debugging and performance tuning

## 2. Components
### CloudWatch Logs
- Synthetic generation logs
- FHIR Data Pipes logs
- OMOP parquet converter logs
- dbt run/test logs

### CloudWatch Metrics
- ECS task CPU/memory
- Step Functions execution counts & failures
- S3 request metrics
- Athena query runtime metrics

### Step Functions Execution History
- Pipeline orchestration auditing  
- Input/output tracking per stage  

### Athena Query Logs
- Stored in CloudTrail + CloudWatch  
- Used to track usage patterns and performance  

## 3. Dashboards
Recommended CloudWatch dashboards:
- ECS Task Utilization
- Pipeline Success Rate
- Athena Performance
- Data ingestion lag (using lineage timestamps)

## 4. Alerts
Use SNS or EventBridge:
- Pipeline failures
- ECS task failures
- Missing partitions or Iceberg metadata errors

