# Step 5: Local Development and Testing

## Overview

Unit tests using pytest and moto for AWS service mocking.

---

## requirements.txt (dev dependencies)

```
boto3>=1.34.0
pytest>=8.0.0
pytest-mock>=3.12.0
moto>=5.0.0
```

---

## tests/fixtures/sample_patient_bundle.json

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "patient-001",
        "identifier": [
          {
            "type": {
              "coding": [{"code": "MR"}]
            },
            "value": "MRN123456"
          }
        ],
        "name": [
          {
            "use": "official",
            "family": "Smith",
            "given": ["John", "Michael"]
          }
        ],
        "birthDate": "1980-01-15",
        "gender": "male"
      }
    },
    {
      "resource": {
        "resourceType": "Encounter",
        "id": "encounter-001",
        "status": "finished",
        "class": {
          "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          "code": "AMB"
        },
        "subject": {
          "reference": "Patient/patient-001"
        },
        "period": {
          "start": "2024-01-15T09:00:00Z",
          "end": "2024-01-15T10:00:00Z"
        }
      }
    },
    {
      "resource": {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {
          "coding": [
            {
              "system": "http://loinc.org",
              "code": "2339-0",
              "display": "Glucose [Mass/volume] in Blood"
            }
          ]
        },
        "subject": {
          "reference": "Patient/patient-001"
        },
        "valueQuantity": {
          "value": 6.5,
          "unit": "%",
          "system": "http://unitsofmeasure.org",
          "code": "%"
        }
      }
    },
    {
      "resource": {
        "resourceType": "Condition",
        "id": "condition-001",
        "clinicalStatus": {
          "coding": [{"code": "active"}]
        },
        "code": {
          "coding": [
            {
              "system": "http://snomed.info/sct",
              "code": "44054006",
              "display": "Type 2 diabetes mellitus"
            }
          ]
        },
        "subject": {
          "reference": "Patient/patient-001"
        }
      }
    }
  ]
}
```

---

## tests/test_fhir_parser.py

```python
import pytest
import json
from fhir_ingestion.fhir_parser import (
    extract_resources_from_bundle,
    bundle_to_ndjson,
    parse_patient_identifiers
)


@pytest.fixture
def sample_bundle():
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "name": [{"use": "official", "family": "Smith", "given": ["John"]}],
                    "birthDate": "1980-01-15",
                    "gender": "male"
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "encounter-001",
                    "status": "finished",
                    "subject": {"reference": "Patient/patient-001"}
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-001",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0"}]},
                    "valueQuantity": {"value": 6.5, "unit": "%"}
                }
            }
        ]
    }


def test_extract_resources_from_bundle(sample_bundle):
    resources = list(extract_resources_from_bundle(sample_bundle))

    assert len(resources) == 3
    assert resources[0]['resourceType'] == 'Patient'
    assert resources[1]['resourceType'] == 'Encounter'
    assert resources[2]['resourceType'] == 'Observation'


def test_extract_single_resource():
    """Test handling of single resource (not a bundle)."""
    single_resource = {
        "resourceType": "Patient",
        "id": "patient-001"
    }

    resources = list(extract_resources_from_bundle(single_resource))

    assert len(resources) == 1
    assert resources[0]['resourceType'] == 'Patient'


def test_bundle_to_ndjson_filters_by_type(sample_bundle):
    patient_ndjson = bundle_to_ndjson(sample_bundle, 'Patient')

    lines = patient_ndjson.strip().split('\n')
    assert len(lines) == 1

    patient = json.loads(lines[0])
    assert patient['resourceType'] == 'Patient'
    assert patient['id'] == 'patient-001'


def test_bundle_to_ndjson_multiple_resources():
    """Test bundle with multiple resources of same type."""
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p1"}},
            {"resource": {"resourceType": "Patient", "id": "p2"}},
            {"resource": {"resourceType": "Encounter", "id": "e1"}}
        ]
    }

    patient_ndjson = bundle_to_ndjson(bundle, 'Patient')
    lines = patient_ndjson.strip().split('\n')

    assert len(lines) == 2
    assert json.loads(lines[0])['id'] == 'p1'
    assert json.loads(lines[1])['id'] == 'p2'


def test_bundle_to_ndjson_no_matching_resources(sample_bundle):
    """Test bundle with no resources of requested type."""
    ndjson = bundle_to_ndjson(sample_bundle, 'MedicationRequest')

    assert ndjson == ''


def test_parse_patient_identifiers():
    patient = {
        "resourceType": "Patient",
        "name": [{"use": "official", "family": "Smith", "given": ["John", "Michael"]}],
        "birthDate": "1980-01-15",
        "gender": "male",
        "identifier": [
            {
                "type": {"coding": [{"code": "MR"}]},
                "value": "MRN123456"
            }
        ]
    }

    identifiers = parse_patient_identifiers(patient)

    assert identifiers['family_name'] == 'Smith'
    assert identifiers['given_names'] == ['John', 'Michael']
    assert identifiers['birth_date'] == '1980-01-15'
    assert identifiers['gender'] == 'male'
    assert identifiers['mrn'] == 'MRN123456'


def test_parse_patient_identifiers_minimal():
    """Test parsing patient with minimal data."""
    patient = {
        "resourceType": "Patient",
        "id": "p1"
    }

    identifiers = parse_patient_identifiers(patient)

    assert identifiers.get('family_name') == ''
    assert identifiers.get('given_names') == []
    assert identifiers.get('birth_date') is None
    assert identifiers.get('gender') is None
```

---

## tests/test_initiate_export.py

```python
import pytest
import boto3
from moto import mock_aws
import json
import os

# Set environment variables before importing handler
os.environ['SOURCE_BUCKET'] = 'healthtech-fhir-source'
os.environ['LANDING_BUCKET'] = 'healthtech-data-lake'

from fhir_ingestion.initiate_export import lambda_handler
from fhir_ingestion.config import Config


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials for moto."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture
def s3_with_bundles(aws_credentials):
    """Create S3 bucket with sample FHIR bundles."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=Config.SOURCE_BUCKET)

        # Upload sample bundles
        for i in range(3):
            s3.put_object(
                Bucket=Config.SOURCE_BUCKET,
                Key=f'synthea/batch-001/patient_{i}.json',
                Body=json.dumps({
                    "resourceType": "Bundle",
                    "entry": [{"resource": {"resourceType": "Patient", "id": f"p{i}"}}]
                })
            )

        yield s3


def test_initiate_synthea_export(s3_with_bundles):
    """Test successful Synthea export initiation."""
    event = {
        "source_prefix": "synthea/batch-001",
        "mode": "synthea"
    }

    result = lambda_handler(event, None)

    assert 'export_id' in result
    assert result['export_id'].startswith('export-')
    assert result['status_payload']['total_files'] == 3
    assert result['status_payload']['mode'] == 'synthea'
    assert result['status_payload']['source_bucket'] == Config.SOURCE_BUCKET
    assert 'initiated_at' in result


def test_initiate_export_with_custom_resource_types(s3_with_bundles):
    """Test export with custom resource type filter."""
    event = {
        "source_prefix": "synthea/batch-001",
        "mode": "synthea",
        "resource_types": ["Patient", "Encounter"]
    }

    result = lambda_handler(event, None)

    assert result['status_payload']['resource_types'] == ["Patient", "Encounter"]


def test_initiate_export_no_files(aws_credentials):
    """Test error when no files found."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=Config.SOURCE_BUCKET)

        event = {
            "source_prefix": "empty/prefix",
            "mode": "synthea"
        }

        with pytest.raises(ValueError, match="No FHIR bundles found"):
            lambda_handler(event, None)


def test_initiate_export_epic_not_implemented(aws_credentials):
    """Test Epic mode raises NotImplementedError."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=Config.SOURCE_BUCKET)

        event = {
            "mode": "epic"
        }

        with pytest.raises(NotImplementedError, match="Epic export not yet implemented"):
            lambda_handler(event, None)


def test_initiate_export_invalid_mode(aws_credentials):
    """Test invalid mode raises ValueError."""
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=Config.SOURCE_BUCKET)

        event = {
            "mode": "invalid"
        }

        with pytest.raises(ValueError, match="Unknown mode"):
            lambda_handler(event, None)
```

---

## tests/test_download_resources.py

```python
import pytest
import boto3
from moto import mock_aws
import json
import os

os.environ['SOURCE_BUCKET'] = 'healthtech-fhir-source'
os.environ['LANDING_BUCKET'] = 'healthtech-data-lake'

from fhir_ingestion.download_resources import lambda_handler
from fhir_ingestion.config import Config


@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture
def s3_setup(aws_credentials):
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')

        # Create buckets
        s3.create_bucket(Bucket=Config.SOURCE_BUCKET)
        s3.create_bucket(Bucket=Config.LANDING_BUCKET)

        # Upload sample bundle
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1", "name": [{"family": "Smith"}]}},
                {"resource": {"resourceType": "Patient", "id": "p2", "name": [{"family": "Jones"}]}},
                {"resource": {"resourceType": "Encounter", "id": "e1", "status": "finished"}}
            ]
        }

        s3.put_object(
            Bucket=Config.SOURCE_BUCKET,
            Key='synthea/batch-001/bundle1.json',
            Body=json.dumps(bundle)
        )

        yield s3


def test_download_resources_success(s3_setup):
    """Test successful resource download and transformation."""
    event = {
        "export_id": "export-test-001",
        "output": {
            "source_bucket": Config.SOURCE_BUCKET,
            "source_prefix": "synthea/batch-001",
            "files": [{"key": "synthea/batch-001/bundle1.json", "size": 100}],
            "resource_types": ["Patient", "Encounter"]
        }
    }

    result = lambda_handler(event, None)

    assert result['export_id'] == "export-test-001"
    assert result['landing_bucket'] == Config.LANDING_BUCKET
    assert result['record_counts']['Patient'] == 2
    assert result['record_counts']['Encounter'] == 1
    assert 'Patient' in result['files_written']
    assert 'Encounter' in result['files_written']
    assert 'completed_at' in result


def test_download_resources_writes_ndjson(s3_setup):
    """Verify NDJSON format in output files."""
    event = {
        "export_id": "export-test-002",
        "output": {
            "source_bucket": Config.SOURCE_BUCKET,
            "source_prefix": "synthea/batch-001",
            "files": [{"key": "synthea/batch-001/bundle1.json", "size": 100}],
            "resource_types": ["Patient"]
        }
    }

    result = lambda_handler(event, None)

    # Read the output file
    s3 = boto3.client('s3', region_name='us-east-1')
    patient_key = result['files_written']['Patient']

    response = s3.get_object(Bucket=Config.LANDING_BUCKET, Key=patient_key)
    content = response['Body'].read().decode('utf-8')

    lines = content.strip().split('\n')
    assert len(lines) == 2

    # Verify valid JSON on each line
    p1 = json.loads(lines[0])
    p2 = json.loads(lines[1])

    assert p1['resourceType'] == 'Patient'
    assert p2['resourceType'] == 'Patient'


def test_download_resources_skips_empty_types(s3_setup):
    """Test handling of resource types with no data."""
    event = {
        "export_id": "export-test-003",
        "output": {
            "source_bucket": Config.SOURCE_BUCKET,
            "source_prefix": "synthea/batch-001",
            "files": [{"key": "synthea/batch-001/bundle1.json", "size": 100}],
            "resource_types": ["Patient", "MedicationRequest"]  # No MedicationRequest in bundle
        }
    }

    result = lambda_handler(event, None)

    assert 'Patient' in result['files_written']
    assert 'MedicationRequest' not in result['files_written']
    assert result['record_counts']['Patient'] == 2
```

---

## Running Tests

```bash
# Navigate to lambda_functions directory
cd lambda_functions

# Install dev dependencies
pip install -r requirements.txt

# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_fhir_parser.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=fhir_ingestion --cov-report=html

# Run tests matching pattern
pytest tests/ -k "test_initiate" -v
```

---

## Local Lambda Invocation (SAM CLI)

```bash
# Build the project
sam build

# Invoke locally with event file
sam local invoke InitiateExportFunction \
  --event tests/events/initiate_event.json

# Start local API (if API Gateway configured)
sam local start-api

# Generate sample event
sam local generate-event s3 put > tests/events/s3_event.json
```

---

## tests/events/initiate_event.json

```json
{
  "source_prefix": "synthea/batch-001",
  "mode": "synthea",
  "resource_types": ["Patient", "Encounter", "Observation", "Condition"]
}
```
