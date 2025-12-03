# FHIR-OMOP Synthetic Stack

A fully deployable **AWS-based reference architecture** for generating, validating, harmonizing, and transforming **synthetic FHIR + OMOP CDM** data using:

- Synthetic data generators (FHIR + OMOP)
- Domain constraints, terminology mappings, and distribution profiles
- AWS S3 + Iceberg + Glue Catalog for the Lakehouse
- Athena for querying
- dbt for semantic modeling, lineage, marts, and metrics layer
- ECS Fargate / Step Functions for pipeline orchestration
- VPC endpoints, IAM, KMS, and Lake Formation for governance

This project is designed for:
- Healthcare data engineering teams  
- AI/ML feature engineering pipelines  
- Compliance-native synthetic data workflows  
- FHIR/OMOP harmonization R&D  
- Early-stage analytics platform prototyping  

---

## Features

### Synthetic Data Layer
- OMOP + FHIR generators
- Domain constraints & medical logic
- Terminology enforcement
- Realistic distributions
- Cross-model validation

### Storage & Modeling
- Iceberg tables on S3
- Glue Catalog metadata
- dbt staging models
- dbt `dim_patient`
- dbt `fact_chronic_condition`
- dbt metrics layer (MetricFlow-ready)

### Orchestration
- ECS Fargate batch tasks
- Step Functions runner:

### Quickstart

<!-- 1. Deploy CDK -->
cd cdk/
npm install
cdk bootstrap
cdk deploy

<!-- 2. Run Synthetic Pipeline -->
aws stepfunctions start-execution \
  --state-machine-arn <your-sm-arn>

<!-- 3. Run dbt -->
cd dbt/fhir_omop_dbt/
dbt seed
dbt run
dbt test

<!-- 4. Query Iceberg tables in Athena -->  
SELECT * FROM fhir_omop_dbt.dim_patient LIMIT 10;

<!-- mkdocs -->
pip install mkdocs mkdocs-material
mkdocs serve
