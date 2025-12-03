# Operations Guide

## 1. Pipeline Execution
Run via Step Functions:
```
aws stepfunctions start-execution --state-machine-arn <ARN>
```

## 2. dbt Operations
```
cd dbt/fhir_omop_dbt
dbt seed
dbt run
dbt test
```

## 3. AWS Athena Queries
Run Iceberg queries via Athena console or CLI:
```
SELECT * FROM fhir_omop.dim_patient LIMIT 20;
```

## 4. Synthetic Pipeline
- Edit configs under `synthetic/config`
- Run local:
```
make -C synthetic
```

## 5. Deployment
```
cd cdk
npm install
cdk synth
cdk deploy
```
