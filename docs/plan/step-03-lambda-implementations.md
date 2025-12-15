# Step 3: Lambda Implementations

## Overview

Core Lambda function implementations for the FHIR ingestion pipeline.

---

## config.py

Shared configuration module.

```python
import os

class Config:
    SOURCE_BUCKET = os.environ.get('SOURCE_BUCKET', 'healthtech-fhir-source')
    LANDING_BUCKET = os.environ.get('LANDING_BUCKET', 'healthtech-data-lake')
    LANDING_PREFIX = os.environ.get('LANDING_PREFIX', 'landing/fhir')
    
    # Resource types to extract (mirrors Epic $export _type parameter)
    RESOURCE_TYPES = [
        'Patient',
        'Encounter', 
        'Observation',
        'Condition',
        'MedicationRequest',
        'Procedure',
        'DiagnosticReport'
    ]
    
    # For future Epic integration
    EPIC_BASE_URL = os.environ.get('EPIC_BASE_URL', '')
    EPIC_CLIENT_ID = os.environ.get('EPIC_CLIENT_ID', '')
```

---

## fhir_parser.py

Shared FHIR parsing utilities.

```python
import json
from typing import Generator, Dict, Any

def extract_resources_from_bundle(bundle: Dict[Any, Any]) -> Generator[Dict[Any, Any], None, None]:
    """
    Extract individual resources from a FHIR Bundle.
    Synthea generates transaction bundles with nested resources.
    """
    if bundle.get('resourceType') != 'Bundle':
        # Single resource, not a bundle
        yield bundle
        return
    
    for entry in bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource:
            yield resource


def bundle_to_ndjson(bundle: Dict[Any, Any], resource_type: str) -> str:
    """
    Convert FHIR Bundle to NDJSON format, filtering by resource type.
    Returns newline-delimited JSON string.
    """
    lines = []
    for resource in extract_resources_from_bundle(bundle):
        if resource.get('resourceType') == resource_type:
            lines.append(json.dumps(resource, separators=(',', ':')))
    return '\n'.join(lines)


def parse_patient_identifiers(patient: Dict[Any, Any]) -> Dict[str, Any]:
    """
    Extract key identifiers from Patient resource for downstream processing.
    """
    identifiers = {}
    
    # Extract MRN or other identifiers
    for identifier in patient.get('identifier', []):
        system = identifier.get('system', '')
        value = identifier.get('value', '')
        
        if 'MR' in identifier.get('type', {}).get('coding', [{}])[0].get('code', ''):
            identifiers['mrn'] = value
        elif 'SSN' in system:
            identifiers['ssn'] = value
        else:
            identifiers.setdefault('other_ids', []).append({
                'system': system,
                'value': value
            })
    
    # Extract name
    names = patient.get('name', [])
    if names:
        official = next((n for n in names if n.get('use') == 'official'), names[0])
        identifiers['family_name'] = official.get('family', '')
        identifiers['given_names'] = official.get('given', [])
    
    # Extract demographics
    identifiers['birth_date'] = patient.get('birthDate')
    identifiers['gender'] = patient.get('gender')
    
    return identifiers
```

---

## initiate_export.py

Lambda 1: Initiate FHIR bulk export.

```python
"""
Lambda 1: Initiate Export

Production behavior (Epic): 
  - POST to $export endpoint
  - Receive Content-Location header for polling

Simulation behavior (Synthea):
  - List objects in source bucket/prefix
  - Return manifest of available files
"""

import json
import logging
import boto3
from datetime import datetime
from config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')


def lambda_handler(event: dict, context) -> dict:
    """
    Initiate FHIR bulk export.
    
    Input event:
    {
        "source_prefix": "synthea/batch-001",  # Optional, defaults to latest
        "resource_types": ["Patient", "Encounter"],  # Optional, defaults to all
        "mode": "synthea"  # or "epic" for production
    }
    
    Output:
    {
        "export_id": "export-20241215-123456",
        "status_payload": {
            "source_bucket": "...",
            "source_prefix": "...",
            "files": [...],
            "resource_types": [...]
        },
        "initiated_at": "2024-12-15T12:34:56Z"
    }
    """
    
    mode = event.get('mode', 'synthea')
    source_prefix = event.get('source_prefix', 'synthea/batch-001')
    resource_types = event.get('resource_types', Config.RESOURCE_TYPES)
    
    export_id = f"export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    
    logger.info(f"Initiating export {export_id} in {mode} mode")
    
    if mode == 'synthea':
        return initiate_synthea_export(export_id, source_prefix, resource_types)
    elif mode == 'epic':
        return initiate_epic_export(export_id, event, resource_types)
    else:
        raise ValueError(f"Unknown mode: {mode}")


def initiate_synthea_export(export_id: str, source_prefix: str, resource_types: list) -> dict:
    """
    List available Synthea bundles in S3.
    """
    
    files = []
    paginator = s3.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=Config.SOURCE_BUCKET, Prefix=source_prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.json'):
                files.append({
                    'key': key,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
    
    logger.info(f"Found {len(files)} bundle files in {Config.SOURCE_BUCKET}/{source_prefix}")
    
    if not files:
        raise ValueError(f"No FHIR bundles found in s3://{Config.SOURCE_BUCKET}/{source_prefix}")
    
    return {
        'export_id': export_id,
        'status_payload': {
            'source_bucket': Config.SOURCE_BUCKET,
            'source_prefix': source_prefix,
            'files': files,
            'resource_types': resource_types,
            'total_files': len(files),
            'mode': 'synthea'
        },
        'initiated_at': datetime.utcnow().isoformat() + 'Z'
    }


def initiate_epic_export(export_id: str, event: dict, resource_types: list) -> dict:
    """
    Initiate Epic Bulk FHIR export.
    Placeholder for production implementation.
    """
    
    # TODO: Implement when Epic sandbox available
    # 1. Get access token from Secrets Manager
    # 2. POST to {epic_base}/Patient/$export
    # 3. Return Content-Location URL
    
    raise NotImplementedError("Epic export not yet implemented")
```

---

## poll_export_status.py

Lambda 2: Poll export status.

```python
"""
Lambda 2: Poll Export Status

Production behavior (Epic):
  - GET Content-Location URL
  - 202 = still processing, retry
  - 200 = complete, return output file URLs

Simulation behavior (Synthea):
  - Always returns "complete" since files are already in S3
  - In production, could add artificial delay for testing retry logic
"""

import json
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context) -> dict:
    """
    Poll export status.
    
    Input event:
    {
        "export_id": "export-20241215-123456",
        "status_payload": { ... from initiate step ... }
    }
    
    Output:
    {
        "export_id": "export-20241215-123456",
        "complete": true,
        "output": {
            "files": [...],
            "resource_types": [...]
        },
        "checked_at": "2024-12-15T12:35:00Z"
    }
    """
    
    export_id = event['export_id']
    status_payload = event['status_payload']
    mode = status_payload.get('mode', 'synthea')
    
    logger.info(f"Polling status for {export_id} in {mode} mode")
    
    if mode == 'synthea':
        return poll_synthea_status(export_id, status_payload)
    elif mode == 'epic':
        return poll_epic_status(export_id, status_payload)
    else:
        raise ValueError(f"Unknown mode: {mode}")


def poll_synthea_status(export_id: str, status_payload: dict) -> dict:
    """
    Synthea files are already available; return complete immediately.
    """
    
    return {
        'export_id': export_id,
        'complete': True,
        'output': {
            'source_bucket': status_payload['source_bucket'],
            'source_prefix': status_payload['source_prefix'],
            'files': status_payload['files'],
            'resource_types': status_payload['resource_types']
        },
        'checked_at': datetime.utcnow().isoformat() + 'Z'
    }


def poll_epic_status(export_id: str, status_payload: dict) -> dict:
    """
    Poll Epic Content-Location URL.
    Placeholder for production implementation.
    """
    
    # TODO: Implement when Epic sandbox available
    # 1. GET status_payload['content_location']
    # 2. If 202: return {'complete': False, 'retry_after': headers['Retry-After']}
    # 3. If 200: parse response, return {'complete': True, 'output': {...}}
    
    raise NotImplementedError("Epic polling not yet implemented")
```

---

## download_resources.py

Lambda 3: Download and transform resources.

```python
"""
Lambda 3: Download and Transform Resources

Production behavior (Epic):
  - Download NDJSON files from Epic-provided URLs
  - Write to S3 landing zone

Simulation behavior (Synthea):
  - Read Synthea bundles from source bucket
  - Parse bundles, extract resources by type
  - Convert to NDJSON format
  - Write to S3 landing zone (same structure as Epic output)
"""

import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List
from config import Config
from fhir_parser import extract_resources_from_bundle

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')


def lambda_handler(event: dict, context) -> dict:
    """
    Download and transform FHIR resources to landing zone.
    
    Input event:
    {
        "export_id": "export-20241215-123456",
        "output": {
            "source_bucket": "...",
            "files": [...],
            "resource_types": [...]
        }
    }
    
    Output:
    {
        "export_id": "export-20241215-123456",
        "landing_bucket": "healthtech-data-lake",
        "files_written": {
            "Patient": "landing/fhir/Patient/2024/12/15/Patient.ndjson",
            "Encounter": "landing/fhir/Encounter/2024/12/15/Encounter.ndjson",
            ...
        },
        "record_counts": {
            "Patient": 1000,
            "Encounter": 5432,
            ...
        },
        "completed_at": "2024-12-15T12:36:00Z"
    }
    """
    
    export_id = event['export_id']
    output = event['output']
    source_bucket = output['source_bucket']
    files = output['files']
    resource_types = output['resource_types']
    
    logger.info(f"Processing {len(files)} files for export {export_id}")
    
    # Accumulate resources by type
    resources_by_type: Dict[str, List[dict]] = {rt: [] for rt in resource_types}
    
    # Process each source file
    for file_info in files:
        key = file_info['key']
        logger.info(f"Processing {key}")
        
        try:
            response = s3.get_object(Bucket=source_bucket, Key=key)
            bundle = json.loads(response['Body'].read().decode('utf-8'))
            
            for resource in extract_resources_from_bundle(bundle):
                resource_type = resource.get('resourceType')
                if resource_type in resources_by_type:
                    resources_by_type[resource_type].append(resource)
                    
        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            raise
    
    # Write NDJSON files to landing zone
    date_path = datetime.utcnow().strftime('%Y/%m/%d')
    files_written = {}
    record_counts = {}
    
    for resource_type, resources in resources_by_type.items():
        if not resources:
            logger.info(f"No {resource_type} resources found")
            continue
        
        # Convert to NDJSON
        ndjson_content = '\n'.join(
            json.dumps(r, separators=(',', ':')) for r in resources
        )
        
        # Write to landing zone
        landing_key = f"{Config.LANDING_PREFIX}/{resource_type}/{date_path}/{resource_type}.ndjson"
        
        s3.put_object(
            Bucket=Config.LANDING_BUCKET,
            Key=landing_key,
            Body=ndjson_content.encode('utf-8'),
            ContentType='application/x-ndjson',
            Metadata={
                'export_id': export_id,
                'resource_type': resource_type,
                'record_count': str(len(resources))
            }
        )
        
        files_written[resource_type] = landing_key
        record_counts[resource_type] = len(resources)
        
        logger.info(f"Wrote {len(resources)} {resource_type} resources to {landing_key}")
    
    return {
        'export_id': export_id,
        'landing_bucket': Config.LANDING_BUCKET,
        'files_written': files_written,
        'record_counts': record_counts,
        'completed_at': datetime.utcnow().isoformat() + 'Z'
    }
```

---

## requirements.txt

```
boto3>=1.34.0
```
