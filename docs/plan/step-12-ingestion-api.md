# Step 12: Ingestion API Implementation

## Overview

Ingestion Service for receiving FHIR data from healthcare organizations via webhooks and presigned URL uploads.

---

## ingestion_api/handler.py

```python
"""
Ingestion API Lambda handler.

Routes:
    POST /v1/ingestion/fhir/Bundle - Receive FHIR Bundle (webhook)
    POST /v1/ingestion/upload-url - Get presigned S3 URL for bulk upload
    GET /v1/ingestion/jobs/{jobId} - Get ingestion job status
"""

import json
import logging
import os
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

from shared.auth import extract_org_context, extract_path_parameter
from shared.exceptions import ValidationError, SecurityError
from shared.organization import OrganizationContext

import webhook_receiver
import presigned_url

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    API Gateway proxy integration handler for ingestion endpoints.
    """
    
    http_method = event.get('httpMethod', 'POST')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    body = event.get('body', '')
    
    request_id = event.get('requestContext', {}).get('requestId', str(uuid.uuid4()))
    
    logger.info(f"Processing {http_method} {path}", extra={'request_id': request_id})
    
    try:
        # Extract organization context
        org_context = extract_org_context(event)
        
        # Route to appropriate handler
        if path.endswith('/fhir/Bundle') and http_method == 'POST':
            result = webhook_receiver.receive_bundle(body, org_context, request_id)
            return success_response(202, result, request_id)  # Accepted
        
        elif path.endswith('/upload-url') and http_method == 'POST':
            result = presigned_url.generate_upload_url(body, org_context, request_id)
            return success_response(200, result, request_id)
        
        elif '/jobs/' in path and http_method == 'GET':
            job_id = path_params.get('jobId')
            if not job_id:
                raise ValidationError("Job ID required")
            result = get_job_status(job_id, org_context)
            return success_response(200, result, request_id)
        
        else:
            raise ValidationError(f"Unknown endpoint: {http_method} {path}")
    
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return error_response(400, str(e), request_id)
    
    except SecurityError as e:
        logger.error(f"Security error: {e}")
        return error_response(403, str(e), request_id)
    
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        return error_response(500, "Internal server error", request_id)


def get_job_status(
    job_id: str,
    org_context: OrganizationContext
) -> Dict[str, Any]:
    """
    Get status of an ingestion job.
    
    In a full implementation, this would query DynamoDB or another
    job tracking store.
    """
    
    # TODO: Implement job tracking with DynamoDB
    # For now, return placeholder
    return {
        "jobId": job_id,
        "organizationId": org_context.organization_id,
        "status": "processing",
        "message": "Job status tracking not yet implemented",
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }


def success_response(
    status_code: int,
    body: Dict[str, Any],
    request_id: str
) -> Dict[str, Any]:
    """Format successful API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-Id': request_id
        },
        'body': json.dumps(body)
    }


def error_response(
    status_code: int,
    message: str,
    request_id: str
) -> Dict[str, Any]:
    """Format error API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-Request-Id': request_id
        },
        'body': json.dumps({
            'error': message,
            'requestId': request_id
        })
    }
```

---

## ingestion_api/webhook_receiver.py

```python
"""
Webhook receiver for real-time FHIR Bundle ingestion.

Receives FHIR Bundles from healthcare organizations and queues
them for asynchronous processing.
"""

import json
import logging
import os
from typing import Any, Dict
from datetime import datetime
import uuid
import hashlib

import boto3

from shared.organization import OrganizationContext
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)

sqs = boto3.client('sqs')
s3 = boto3.client('s3')


def receive_bundle(
    body: str,
    org_context: OrganizationContext,
    request_id: str
) -> Dict[str, Any]:
    """
    Receive FHIR Bundle via webhook.
    
    Args:
        body: Raw request body (FHIR Bundle JSON)
        org_context: Organization context from authorizer
        request_id: Request ID for tracing
    
    Returns:
        Job status response
    """
    
    # Parse and validate bundle
    bundle = parse_bundle(body)
    
    # Generate job ID
    job_id = generate_job_id(org_context.organization_id, request_id)
    
    # Store raw bundle in S3 for processing
    s3_key = store_bundle(bundle, org_context, job_id)
    
    # Queue for async processing
    queue_for_processing(job_id, s3_key, org_context)
    
    logger.info(
        f"Bundle received and queued: {job_id}",
        extra={
            'job_id': job_id,
            's3_key': s3_key,
            **org_context.to_log_context()
        }
    )
    
    return {
        "jobId": job_id,
        "status": "accepted",
        "message": "Bundle accepted for processing",
        "resourceCount": count_resources(bundle),
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }


def parse_bundle(body: str) -> Dict[str, Any]:
    """
    Parse and validate FHIR Bundle.
    
    Raises:
        ValidationError: If body is not valid FHIR Bundle
    """
    
    if not body:
        raise ValidationError("Request body is empty")
    
    try:
        bundle = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}")
    
    # Validate FHIR Bundle structure
    if bundle.get('resourceType') != 'Bundle':
        raise ValidationError(
            f"Expected resourceType 'Bundle', got '{bundle.get('resourceType')}'"
        )
    
    bundle_type = bundle.get('type')
    if bundle_type not in ['transaction', 'batch', 'collection', 'message']:
        raise ValidationError(f"Unsupported bundle type: {bundle_type}")
    
    entries = bundle.get('entry', [])
    if not entries:
        raise ValidationError("Bundle contains no entries")
    
    # Validate each entry has a resource
    for i, entry in enumerate(entries):
        if 'resource' not in entry:
            raise ValidationError(f"Entry {i} missing 'resource' field")
    
    return bundle


def generate_job_id(organization_id: str, request_id: str) -> str:
    """Generate unique job ID."""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique = hashlib.md5(f"{request_id}{timestamp}".encode()).hexdigest()[:8]
    return f"job-{organization_id[:8]}-{timestamp}-{unique}"


def store_bundle(
    bundle: Dict[str, Any],
    org_context: OrganizationContext,
    job_id: str
) -> str:
    """
    Store raw bundle in S3 for processing.
    
    Returns:
        S3 key where bundle is stored
    """
    
    bucket = os.environ['UPLOAD_BUCKET']
    prefix = os.environ.get('UPLOAD_PREFIX', 'incoming/fhir')
    
    # Organize by org and date
    date_path = datetime.utcnow().strftime('%Y/%m/%d')
    s3_key = f"{prefix}/{org_context.organization_id}/{date_path}/{job_id}.json"
    
    s3.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=json.dumps(bundle),
        ContentType='application/fhir+json',
        Metadata={
            'job_id': job_id,
            'organization_id': org_context.organization_id,
            'bundle_type': bundle.get('type', 'unknown'),
            'entry_count': str(len(bundle.get('entry', [])))
        }
    )
    
    return s3_key


def queue_for_processing(
    job_id: str,
    s3_key: str,
    org_context: OrganizationContext
) -> None:
    """
    Send message to SQS for async processing.
    """
    
    queue_url = os.environ['INGESTION_QUEUE_URL']
    
    message = {
        'jobId': job_id,
        's3Bucket': os.environ['UPLOAD_BUCKET'],
        's3Key': s3_key,
        'organizationId': org_context.organization_id,
        'organizationName': org_context.organization_name,
        'userId': org_context.user_id,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
        MessageAttributes={
            'organizationId': {
                'DataType': 'String',
                'StringValue': org_context.organization_id
            },
            'jobId': {
                'DataType': 'String',
                'StringValue': job_id
            }
        },
        MessageGroupId=org_context.organization_id  # FIFO ordering by org
    )


def count_resources(bundle: Dict[str, Any]) -> Dict[str, int]:
    """Count resources by type in bundle."""
    counts: Dict[str, int] = {}
    
    for entry in bundle.get('entry', []):
        resource = entry.get('resource', {})
        resource_type = resource.get('resourceType', 'Unknown')
        counts[resource_type] = counts.get(resource_type, 0) + 1
    
    return counts
```

---

## ingestion_api/presigned_url.py

```python
"""
Presigned URL generator for bulk FHIR data uploads.

Allows healthcare organizations to upload large files directly
to S3 without going through API Gateway.
"""

import json
import logging
import os
from typing import Any, Dict
from datetime import datetime
import uuid

import boto3
from botocore.config import Config

from shared.organization import OrganizationContext
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Configure S3 client with signature v4 (required for presigned URLs)
s3 = boto3.client(
    's3',
    config=Config(signature_version='s3v4')
)


def generate_upload_url(
    body: str,
    org_context: OrganizationContext,
    request_id: str
) -> Dict[str, Any]:
    """
    Generate presigned S3 URL for bulk file upload.
    
    Args:
        body: Request body with upload parameters
        org_context: Organization context
        request_id: Request ID for tracing
    
    Returns:
        Presigned URL and upload instructions
    """
    
    # Parse request
    params = parse_request(body)
    
    # Generate unique upload key
    upload_id = generate_upload_id(org_context.organization_id)
    
    # Determine S3 key based on content type
    content_type = params.get('contentType', 'application/fhir+json')
    file_extension = get_file_extension(content_type)
    
    bucket = os.environ['UPLOAD_BUCKET']
    prefix = os.environ.get('UPLOAD_PREFIX', 'incoming/fhir')
    date_path = datetime.utcnow().strftime('%Y/%m/%d')
    
    s3_key = f"{prefix}/{org_context.organization_id}/{date_path}/{upload_id}{file_extension}"
    
    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': s3_key,
            'ContentType': content_type,
            'Metadata': {
                'organization_id': org_context.organization_id,
                'upload_id': upload_id,
                'uploaded_by': org_context.user_id or 'unknown'
            }
        },
        ExpiresIn=3600,  # URL valid for 1 hour
        HttpMethod='PUT'
    )
    
    logger.info(
        f"Generated presigned URL: {upload_id}",
        extra={
            'upload_id': upload_id,
            's3_key': s3_key,
            **org_context.to_log_context()
        }
    )
    
    return {
        "uploadId": upload_id,
        "uploadUrl": presigned_url,
        "method": "PUT",
        "headers": {
            "Content-Type": content_type
        },
        "expiresIn": 3600,
        "expiresAt": (datetime.utcnow().timestamp() + 3600),
        "s3Bucket": bucket,
        "s3Key": s3_key,
        "instructions": {
            "1": f"Use HTTP PUT to upload your file to the uploadUrl",
            "2": f"Set Content-Type header to '{content_type}'",
            "3": "URL expires in 1 hour",
            "4": "After upload, file will be automatically processed"
        }
    }


def parse_request(body: str) -> Dict[str, Any]:
    """Parse and validate upload URL request."""
    
    if not body:
        return {}
    
    try:
        params = json.loads(body)
    except json.JSONDecodeError:
        return {}
    
    # Validate content type if provided
    content_type = params.get('contentType', '')
    valid_types = [
        'application/fhir+json',
        'application/json',
        'application/fhir+ndjson',
        'application/x-ndjson'
    ]
    
    if content_type and content_type not in valid_types:
        raise ValidationError(
            f"Invalid contentType '{content_type}'. "
            f"Allowed types: {', '.join(valid_types)}"
        )
    
    return params


def generate_upload_id(organization_id: str) -> str:
    """Generate unique upload ID."""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique = uuid.uuid4().hex[:8]
    return f"upload-{timestamp}-{unique}"


def get_file_extension(content_type: str) -> str:
    """Get file extension for content type."""
    extensions = {
        'application/fhir+json': '.json',
        'application/json': '.json',
        'application/fhir+ndjson': '.ndjson',
        'application/x-ndjson': '.ndjson'
    }
    return extensions.get(content_type, '.json')
```

---

## ingestion_api/requirements.txt

```
boto3>=1.34.0
```

---

## S3 Event Trigger for Processing Uploads

When files are uploaded via presigned URL, trigger the existing batch processing pipeline.

### s3_trigger_config.yaml (add to template-api.yaml)

```yaml
  # S3 Event trigger for uploaded files
  UploadProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-upload-processor-${Environment}
      Handler: upload_processor.lambda_handler
      CodeUri: ingestion_api/
      Description: Process files uploaded via presigned URL
      Timeout: 60
      MemorySize: 512
      Environment:
        Variables:
          INGESTION_QUEUE_URL: !Ref IngestionQueue
      Policies:
        - S3ReadPolicy:
            BucketName: !Sub healthtech-data-lake-${Environment}
        - SQSSendMessagePolicy:
            QueueName: !GetAtt IngestionQueue.QueueName
      Events:
        S3Upload:
          Type: S3
          Properties:
            Bucket: !Ref DataLakeBucket
            Events: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: incoming/fhir/
```

---

## ingestion_api/upload_processor.py

```python
"""
Process files uploaded via presigned URL.

Triggered by S3 event when new files are uploaded to incoming/fhir/ prefix.
"""

import json
import logging
import os
from typing import Any, Dict
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
s3 = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Process S3 upload event.
    
    Extracts metadata and queues file for processing.
    """
    
    processed = 0
    errors = 0
    
    for record in event.get('Records', []):
        try:
            process_record(record)
            processed += 1
        except Exception as e:
            logger.exception(f"Error processing record: {e}")
            errors += 1
    
    return {
        'processed': processed,
        'errors': errors
    }


def process_record(record: Dict[str, Any]) -> None:
    """Process single S3 event record."""
    
    # Extract S3 info
    bucket = record['s3']['bucket']['name']
    key = unquote_plus(record['s3']['object']['key'])
    size = record['s3']['object'].get('size', 0)
    
    logger.info(f"Processing uploaded file: s3://{bucket}/{key}")
    
    # Get object metadata
    response = s3.head_object(Bucket=bucket, Key=key)
    metadata = response.get('Metadata', {})
    
    organization_id = metadata.get('organization_id')
    upload_id = metadata.get('upload_id')
    
    if not organization_id:
        # Try to extract from key path
        # Format: incoming/fhir/{org_id}/{date}/{upload_id}.json
        parts = key.split('/')
        if len(parts) >= 3:
            organization_id = parts[2]
    
    if not organization_id:
        logger.error(f"Cannot determine organization_id for {key}")
        raise ValueError("Missing organization_id")
    
    # Generate job ID
    job_id = upload_id or key.split('/')[-1].replace('.json', '').replace('.ndjson', '')
    
    # Queue for processing
    queue_url = os.environ['INGESTION_QUEUE_URL']
    
    message = {
        'jobId': job_id,
        's3Bucket': bucket,
        's3Key': key,
        'organizationId': organization_id,
        'fileSize': size,
        'source': 'presigned_upload',
        'timestamp': record['eventTime']
    }
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
        MessageAttributes={
            'organizationId': {
                'DataType': 'String',
                'StringValue': organization_id
            },
            'source': {
                'DataType': 'String',
                'StringValue': 'presigned_upload'
            }
        }
    )
    
    logger.info(f"Queued upload for processing: {job_id}")
```

---

## Testing Ingestion API

### Test webhook endpoint

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name healthtech-fhir-api-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

# Create test bundle
cat > /tmp/test_bundle.json << 'EOF'
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "test-patient-1",
        "name": [{"family": "Test", "given": ["Patient"]}],
        "gender": "male",
        "birthDate": "1990-01-01"
      }
    }
  ]
}
EOF

# Send bundle via webhook
curl -X POST "${API_ENDPOINT}/v1/ingestion/fhir/Bundle" \
    -H "Authorization: Bearer ${JWT_TOKEN}" \
    -H "Content-Type: application/fhir+json" \
    -d @/tmp/test_bundle.json
```

### Test presigned URL endpoint

```bash
# Request presigned URL
RESPONSE=$(curl -s -X POST "${API_ENDPOINT}/v1/ingestion/upload-url" \
    -H "Authorization: Bearer ${JWT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"contentType": "application/fhir+ndjson"}')

echo $RESPONSE | jq .

# Extract upload URL
UPLOAD_URL=$(echo $RESPONSE | jq -r '.uploadUrl')

# Upload file using presigned URL
curl -X PUT "$UPLOAD_URL" \
    -H "Content-Type: application/fhir+ndjson" \
    --data-binary @/path/to/your/data.ndjson
```

### Check job status

```bash
# Get job ID from webhook response
JOB_ID="job-org123-20241215-abc12345"

# Check status
curl -X GET "${API_ENDPOINT}/v1/ingestion/jobs/${JOB_ID}" \
    -H "Authorization: Bearer ${JWT_TOKEN}"
```
