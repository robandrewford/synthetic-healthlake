# Cost Management Strategy

## 1. Guiding Principles
- Optimize compute first (ECS tasks)
- Minimize unnecessary Athena scans
- Store data efficiently using Iceberg partitioning

## 2. Major Cost Areas
- **ECS Fargate**: per-task compute
- **Athena**: per-TB scanned
- **S3 storage**: Iceberg tables + logs
- **Glue Catalog**: small metadata cost

## 3. Optimization Strategies
### ECS
- Use Fargate Spot for non-critical tasks  
- Right-size CPU/memory for synthetic + dbt runs  
- Avoid long-running ECS services unless necessary  

### Athena
- Partition Iceberg tables:  
  - `year_of_birth` for OMOP person  
  - `birth_date` for FHIR patient  
- Avoid SELECT * in dashboards  
- Use CTAS tables for repeated queries  

### S3
- Enable lifecycle rules:  
  - Raw data → expire after 30 days  
  - Logs → expire after 14 days  

### CI/CD
- Cache npm/pip packages  
- Avoid running dbt tests on every commit unless changed  

## 4. Monitoring
Use AWS Cost Explorer alerts:
- Monthly Fargate spend threshold  
- Athena query cost anomalies  
