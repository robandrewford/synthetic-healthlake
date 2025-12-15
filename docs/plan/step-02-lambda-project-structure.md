# Step 2: Lambda Project Structure

## Overview

Directory structure for the FHIR ingestion Lambda pipeline using AWS SAM.

---

## Project Structure

```
lambda_functions/
├── fhir_ingestion/
│   ├── __init__.py
│   ├── initiate_export.py      # Lambda 1
│   ├── poll_export_status.py   # Lambda 2
│   ├── download_resources.py   # Lambda 3
│   ├── fhir_parser.py          # Shared: Bundle → NDJSON conversion
│   ├── config.py               # Environment config
│   └── requirements.txt
├── tests/
│   ├── __init__.py
│   ├── test_initiate_export.py
│   ├── test_poll_status.py
│   ├── test_download_resources.py
│   ├── test_fhir_parser.py
│   └── fixtures/
│       └── sample_patient_bundle.json
├── statemachine/
│   └── fhir_ingestion.asl.json
├── template.yaml               # SAM template
└── samconfig.toml              # SAM deployment config
```

---

## Scaffold Commands

```bash
# Create directory structure
mkdir -p lambda_functions/{fhir_ingestion,tests/fixtures,statemachine}

# Create __init__.py files
touch lambda_functions/fhir_ingestion/__init__.py
touch lambda_functions/tests/__init__.py

# Create placeholder files
touch lambda_functions/fhir_ingestion/{config,fhir_parser,initiate_export,poll_export_status,download_resources}.py
touch lambda_functions/fhir_ingestion/requirements.txt
touch lambda_functions/tests/{test_fhir_parser,test_initiate_export,test_poll_status,test_download_resources}.py
touch lambda_functions/template.yaml
touch lambda_functions/statemachine/fhir_ingestion.asl.json
```

---

## SAM CLI Installation

```bash
# macOS
brew install aws-sam-cli

# Linux
pip install aws-sam-cli

# Verify installation
sam --version
```
