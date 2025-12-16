"""
Webhook Ingestion API Lambda handler.

Implements:
- POST /ingestion/fhir/Bundle - Receive FHIR Bundle via webhook
- GET /ingestion/jobs/{jobId} - Get job status

Receives FHIR Bundles from healthcare organizations and queues
them for asynchronous processing.

Reference: docs/plan/step-12-ingestion-api.md
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

# Environment configuration
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET", "healthtech-data-lake")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "incoming/fhir")
INGESTION_QUEUE_URL = os.environ.get("INGESTION_QUEUE_URL", "")


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    API Gateway proxy integration handler for webhook ingestion.

    Routes:
        POST /ingestion/fhir/Bundle - Receive FHIR Bundle
        GET /ingestion/jobs/{jobId} - Get job status
    """
    try:
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        body = event.get("body", "")

        request_id = event.get("requestContext", {}).get("requestId", str(uuid.uuid4()))

        logger.info(f"Processing {http_method} {path}", extra={"request_id": request_id})

        # Route to appropriate handler
        if "/Bundle" in path and http_method == "POST":
            return receive_bundle(body, request_id)

        elif "/jobs/" in path and http_method == "GET":
            job_id = path_params.get("jobId")
            if not job_id:
                return error_response(400, "Job ID required")
            return get_job_status(job_id)

        else:
            return error_response(400, f"Unknown endpoint: {http_method} {path}")

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return error_response(400, str(e))

    except Exception as e:
        logger.exception(f"Error in webhook handler: {e}")
        return error_response(500, "Internal Server Error")


def receive_bundle(body: str, request_id: str) -> dict[str, Any]:
    """
    Receive FHIR Bundle via webhook.

    Args:
        body: Raw request body (FHIR Bundle JSON)
        request_id: Request ID for tracing

    Returns:
        API Gateway response with job status
    """
    # Parse and validate bundle
    bundle = parse_bundle(body)

    # Generate job ID
    job_id = generate_job_id(request_id)

    # Store raw bundle in S3 for processing
    s3_key = store_bundle(bundle, job_id)

    # Queue for async processing
    queue_for_processing(job_id, s3_key)

    logger.info(
        f"Bundle received and queued: {job_id}",
        extra={"job_id": job_id, "s3_key": s3_key, "request_id": request_id},
    )

    response_body = {
        "jobId": job_id,
        "status": "accepted",
        "message": "Bundle accepted for processing",
        "resourceCount": count_resources(bundle),
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }

    return {
        "statusCode": 202,  # Accepted
        "headers": {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
            "X-Job-Id": job_id,
        },
        "body": json.dumps(response_body),
    }


def parse_bundle(body: str) -> dict[str, Any]:
    """
    Parse and validate FHIR Bundle.

    Args:
        body: Raw JSON body

    Returns:
        Parsed Bundle dict

    Raises:
        ValidationError: If body is not valid FHIR Bundle
    """
    if not body:
        raise ValidationError("Request body is empty")

    try:
        bundle = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {e}") from e

    # Validate FHIR Bundle structure
    if bundle.get("resourceType") != "Bundle":
        raise ValidationError(f"Expected resourceType 'Bundle', got '{bundle.get('resourceType')}'")

    bundle_type = bundle.get("type")
    valid_types = ["transaction", "batch", "collection", "message", "document"]
    if bundle_type not in valid_types:
        raise ValidationError(f"Unsupported bundle type: {bundle_type}. Valid types: {valid_types}")

    entries = bundle.get("entry", [])
    if not entries:
        raise ValidationError("Bundle contains no entries")

    # Validate each entry has a resource
    for i, entry in enumerate(entries):
        if "resource" not in entry:
            raise ValidationError(f"Entry {i} missing 'resource' field")

    return bundle


def generate_job_id(request_id: str) -> str:
    """Generate unique job ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique = hashlib.md5(f"{request_id}{timestamp}".encode()).hexdigest()[:8]
    return f"job-{timestamp}-{unique}"


def store_bundle(bundle: dict[str, Any], job_id: str) -> str:
    """
    Store raw bundle in S3 for processing.

    Args:
        bundle: Parsed FHIR Bundle
        job_id: Job identifier

    Returns:
        S3 key where bundle is stored
    """
    # Organize by date
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    s3_key = f"{UPLOAD_PREFIX}/webhooks/{date_path}/{job_id}.json"

    s3_client.put_object(
        Bucket=UPLOAD_BUCKET,
        Key=s3_key,
        Body=json.dumps(bundle),
        ContentType="application/fhir+json",
        Metadata={
            "job_id": job_id,
            "bundle_type": bundle.get("type", "unknown"),
            "entry_count": str(len(bundle.get("entry", []))),
            "source": "webhook",
        },
    )

    return s3_key


def queue_for_processing(job_id: str, s3_key: str) -> None:
    """
    Send message to SQS for async processing.

    Args:
        job_id: Job identifier
        s3_key: S3 key of stored bundle
    """
    if not INGESTION_QUEUE_URL:
        logger.warning("INGESTION_QUEUE_URL not configured, skipping queue")
        return

    message = {
        "jobId": job_id,
        "s3Bucket": UPLOAD_BUCKET,
        "s3Key": s3_key,
        "source": "webhook",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    sqs_client.send_message(
        QueueUrl=INGESTION_QUEUE_URL,
        MessageBody=json.dumps(message),
        MessageAttributes={
            "source": {"DataType": "String", "StringValue": "webhook"},
            "jobId": {"DataType": "String", "StringValue": job_id},
        },
    )


def count_resources(bundle: dict[str, Any]) -> dict[str, int]:
    """Count resources by type in bundle."""
    counts: dict[str, int] = {}

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType", "Unknown")
        counts[resource_type] = counts.get(resource_type, 0) + 1

    return counts


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Get status of an ingestion job.

    In a full implementation, this would query DynamoDB or another
    job tracking store. For now, we check if the file exists in S3.

    Args:
        job_id: Job identifier

    Returns:
        API Gateway response with job status
    """
    logger.info(f"Getting status for job: {job_id}")

    # Try to find the job file in S3
    # Parse date from job ID: job-YYYYMMDDHHMMSS-hash
    try:
        parts = job_id.split("-")
        if len(parts) >= 2:
            timestamp_str = parts[1]
            year = timestamp_str[:4]
            month = timestamp_str[4:6]
            day = timestamp_str[6:8]
            date_path = f"{year}/{month}/{day}"
        else:
            date_path = datetime.utcnow().strftime("%Y/%m/%d")
    except Exception:
        date_path = datetime.utcnow().strftime("%Y/%m/%d")

    s3_key = f"{UPLOAD_PREFIX}/webhooks/{date_path}/{job_id}.json"

    try:
        # Check if file exists
        response = s3_client.head_object(Bucket=UPLOAD_BUCKET, Key=s3_key)

        status_response = {
            "jobId": job_id,
            "status": "processing",
            "message": "Bundle received and queued for processing",
            "s3Key": s3_key,
            "metadata": {
                "size": response.get("ContentLength", 0),
                "lastModified": response.get("LastModified", "").isoformat()
                if response.get("LastModified")
                else None,
                "entryCount": response.get("Metadata", {}).get("entry_count"),
            },
            "createdAt": response.get("LastModified", "").isoformat()
            if response.get("LastModified")
            else None,
        }

        return success_response(status_response)

    except s3_client.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return error_response(404, f"Job not found: {job_id}")
        raise


def success_response(body: Any) -> dict[str, Any]:
    """Format successful API response."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    """Format error API response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message, "statusCode": status_code}),
    }


class ValidationError(Exception):
    """Raised when request validation fails."""

    pass
