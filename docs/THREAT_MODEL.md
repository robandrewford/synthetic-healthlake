# Threat Model

## 1. Scope
Covers synthetic data pipelines, S3/Iceberg storage, ECS compute, Step Functions, dbt, and AWS access patterns.

## 2. Assets
- Synthetic FHIR + OMOP datasets
- Transformation logic (dbt + ETL)
- AWS infrastructure (S3, Glue, ECS, VPC)
- Governance and lineage metadata

## 3. Actors
### Internal
- Developers with commit access
- CI/CD workflows
- dbt runners / ECS tasks

### External
- Unauthorized AWS users
- Attackers trying to access S3 buckets or credentials

## 4. Threats
### T1 — Unauthorized Access to S3 Buckets
**Impact:** High  
**Mitigations:**
- VPC endpoints + no public access  
- KMS encryption  
- IAM least privilege  
- Lake Formation (future)

### T2 — Compromised GitHub Secrets
**Impact:** High  
**Mitigations:**
- Rotate secrets frequently  
- Use GitHub OIDC for AWS access  

### T3 — Malicious Code Injection in Synthetic Scripts
**Impact:** Medium  
**Mitigations:**
- CI pipeline requires smoke test compilation  
- PR review required for Python changes  

### T4 — Privilege Escalation via ECS Task Role
**Impact:** High  
**Mitigations:**
- Narrow IAM policies  
- Use dedicated roles per task type  

### T5 — dbt Exposure of Sensitive Data
Not applicable (synthetic only), but:  
**Mitigations:**  
- Continue enforcing synthetic-only data  
- Add schema guards  

