# Step 7: API Project Structure Extension

## Overview

Extend the Lambda project structure to support Bezos Mandate-compliant API layer with organization-scoped data access.

---

## Extended Project Structure

```
lambda_functions/
├── fhir_ingestion/           # Existing batch ingestion (Steps 1-6)
│   ├── __init__.py
│   ├── config.py
│   ├── fhir_parser.py
│   ├── initiate_export.py
│   ├── poll_export_status.py
│   ├── download_resources.py
│   └── requirements.txt
│
├── api_authorizer/           # NEW: JWT/OAuth validation
│   ├── __init__.py
│   ├── handler.py
│   └── requirements.txt
│
├── fhir_api/                 # NEW: Data Access Service
│   ├── __init__.py
│   ├── handler.py
│   ├── patient.py
│   ├── encounter.py
│   ├── observation.py
│   ├── snowflake_client.py
│   └── requirements.txt
│
├── ingestion_api/            # NEW: Ingestion Service (sync/webhook)
│   ├── __init__.py
│   ├── handler.py
│   ├── presigned_url.py
│   ├── webhook_receiver.py
│   └── requirements.txt
│
├── export_api/               # FUTURE: Export Service
│   ├── __init__.py
│   ├── handler.py
│   └── requirements.txt
│
├── shared/                   # NEW: Shared utilities across API Lambdas
│   ├── __init__.py
│   ├── auth.py
│   ├── organization.py
│   ├── fhir_utils.py
│   └── exceptions.py
│
├── tests/
│   ├── __init__.py
│   ├── test_fhir_parser.py
│   ├── test_initiate_export.py
│   ├── test_poll_status.py
│   ├── test_download_resources.py
│   ├── test_api_authorizer.py      # NEW
│   ├── test_fhir_api.py            # NEW
│   ├── test_organization_scope.py  # NEW
│   └── fixtures/
│       ├── sample_patient_bundle.json
│       └── sample_jwt_token.json   # NEW
│
├── statemachine/
│   └── fhir_ingestion.asl.json
│
├── template.yaml             # Batch ingestion SAM template
├── template-api.yaml         # NEW: API layer SAM template
└── samconfig.toml
```

---

## Scaffold Commands

```bash
cd lambda_functions

# Create API directories
mkdir -p api_authorizer fhir_api ingestion_api export_api shared

# Create __init__.py files
touch api_authorizer/__init__.py
touch fhir_api/__init__.py
touch ingestion_api/__init__.py
touch export_api/__init__.py
touch shared/__init__.py

# Create placeholder files for api_authorizer
touch api_authorizer/{handler,requirements}.txt
mv api_authorizer/requirements.txt api_authorizer/requirements.txt

# Create placeholder files for fhir_api
touch fhir_api/{handler,patient,encounter,observation,snowflake_client}.py
touch fhir_api/requirements.txt

# Create placeholder files for ingestion_api
touch ingestion_api/{handler,presigned_url,webhook_receiver}.py
touch ingestion_api/requirements.txt

# Create placeholder files for shared
touch shared/{auth,organization,fhir_utils,exceptions}.py

# Create test files
touch tests/{test_api_authorizer,test_fhir_api,test_organization_scope}.py
touch tests/fixtures/sample_jwt_token.json

# Create API SAM template
touch template-api.yaml
```

---

## Dependency Files

### api_authorizer/requirements.txt

```
PyJWT>=2.8.0
cryptography>=41.0.0
boto3>=1.34.0
```

### fhir_api/requirements.txt

```
snowflake-connector-python>=3.6.0
boto3>=1.34.0
```

### ingestion_api/requirements.txt

```
boto3>=1.34.0
```

### shared/requirements.txt

```
# Shared utilities have no additional dependencies
# All dependencies come from the Lambda that imports shared
```

---

## Layer Configuration (Optional)

For shared code, consider AWS Lambda Layers:

```yaml
# In template-api.yaml
Resources:
  SharedLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: healthtech-shared
      Description: Shared utilities for API Lambdas
      ContentUri: shared/
      CompatibleRuntimes:
        - python3.11
      RetentionPolicy: Retain
```

Alternative: Copy `shared/` into each Lambda's CodeUri during build.

---

## Build Script for Shared Code

```bash
#!/bin/bash
# scripts/build_api_lambdas.sh

set -e

# Copy shared code into each API Lambda directory
for dir in api_authorizer fhir_api ingestion_api export_api; do
    if [ -d "lambda_functions/$dir" ]; then
        echo "Copying shared/ to $dir"
        cp -r lambda_functions/shared lambda_functions/$dir/
    fi
done

# Build with SAM
sam build --template template-api.yaml
```

---

## Verification

```bash
# Verify structure
tree lambda_functions/ -I '__pycache__|*.pyc'

# Verify imports work
cd lambda_functions
python -c "from shared.organization import OrganizationContext; print('OK')"
python -c "from shared.exceptions import SecurityError; print('OK')"
```
