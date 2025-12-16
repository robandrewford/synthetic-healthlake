"""
Presigned URL Upload API Lambda handler.

Implements:
- POST /ingestion/upload-url - Generate presigned S3 URL for bulk upload

Allows healthcare organizations to upload large FHIR files directly
to S3 without going through API Gateway size limits.

Reference: docs/plan/step-12-ingestion-api.md
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure S3 client with signature v4 (required for presigned URLs)
s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

# Environment configuration
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET", "healthtech-data-lake")
UPLOAD_PREFIX = os.environ.get("UPLOAD_PREFIX", "incoming/fhir")
PRESIGNED_URL_EXPIRY = int(os.environ.get("PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour default

# Valid content types for FHIR uploads
VALID_CONTENT_TYPES = [
    "application/fhir+json",
    "application/json",
    "application/fhir+ndjson",
    "application/x-ndjson",
]


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    API Gateway proxy integration handler for presigned URL generation.

    Routes:
        POST /ingestion/upload-url - Generate presigned upload URL
    """
    try:
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        body = event.get("body", "")

        request_id = event.get("requestContext", {}).get("requestId", str(uuid.uuid4()))

        logger.info(f"Processing {http_method} {path}", extra={"request_id": request_id})

        # Route to appropriate handler
        if "/upload-url" in path and http_method == "POST":
            return generate_upload_url(body, request_id)
        else:
            return error_response(400, f"Unknown endpoint: {http_method} {path}")

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return error_response(400, str(e))

    except Exception as e:
        logger.exception(f"Error in presigned URL handler: {e}")
        return error_response(500, "Internal Server Error")


def generate_upload_url(body: str, request_id: str) -> dict[str, Any]:
    """
    Generate presigned S3 URL for bulk file upload.

    Args:
        body: Request body with upload parameters
        request_id: Request ID for tracing

    Returns:
        API Gateway response with presigned URL and upload instructions
    """
    # Parse request
    params = parse_request(body)

    # Generate unique upload ID
    upload_id = generate_upload_id()

    # Determine content type and file extension
    content_type = params.get("contentType", "application/fhir+json")
    file_extension = get_file_extension(content_type)

    # Build S3 key with date partitioning
    date_path = datetime.utcnow().strftime("%Y/%m/%d")
    s3_key = f"{UPLOAD_PREFIX}/uploads/{date_path}/{upload_id}{file_extension}"

    # Optional filename from request
    filename = params.get("filename")
    if filename:
        # Sanitize filename and use for key
        safe_filename = sanitize_filename(filename)
        s3_key = f"{UPLOAD_PREFIX}/uploads/{date_path}/{upload_id}-{safe_filename}"

    # Generate presigned URL
    presigned_url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": UPLOAD_BUCKET,
            "Key": s3_key,
            "ContentType": content_type,
            "Metadata": {
                "upload_id": upload_id,
                "request_id": request_id,
                "source": "presigned_upload",
            },
        },
        ExpiresIn=PRESIGNED_URL_EXPIRY,
        HttpMethod="PUT",
    )

    expires_at = datetime.utcnow().timestamp() + PRESIGNED_URL_EXPIRY

    logger.info(
        f"Generated presigned URL: {upload_id}",
        extra={
            "upload_id": upload_id,
            "s3_key": s3_key,
            "request_id": request_id,
            "content_type": content_type,
        },
    )

    response_body = {
        "uploadId": upload_id,
        "uploadUrl": presigned_url,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
        "s3Bucket": UPLOAD_BUCKET,
        "s3Key": s3_key,
        "expiresIn": PRESIGNED_URL_EXPIRY,
        "expiresAt": expires_at,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "instructions": {
            "1": "Use HTTP PUT to upload your file to the uploadUrl",
            "2": f"Set Content-Type header to '{content_type}'",
            "3": f"URL expires in {PRESIGNED_URL_EXPIRY // 60} minutes",
            "4": "After upload, file will be automatically processed",
        },
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
            "X-Upload-Id": upload_id,
        },
        "body": json.dumps(response_body),
    }


def parse_request(body: str) -> dict[str, Any]:
    """
    Parse and validate upload URL request.

    Args:
        body: Raw JSON body

    Returns:
        Parsed parameters dict

    Raises:
        ValidationError: If parameters are invalid
    """
    if not body:
        return {}

    try:
        params = json.loads(body)
    except json.JSONDecodeError:
        return {}

    # Validate content type if provided
    content_type = params.get("contentType", "")
    if content_type and content_type not in VALID_CONTENT_TYPES:
        raise ValidationError(
            f"Invalid contentType '{content_type}'. Allowed types: {', '.join(VALID_CONTENT_TYPES)}"
        )

    # Validate optional parameters
    if "expiresIn" in params:
        expires_in = params["expiresIn"]
        if not isinstance(expires_in, int) or expires_in < 60 or expires_in > 86400:
            raise ValidationError("expiresIn must be an integer between 60 and 86400 seconds")

    return params


def generate_upload_id() -> str:
    """Generate unique upload ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:8]
    return f"upload-{timestamp}-{unique}"


def get_file_extension(content_type: str) -> str:
    """Get file extension for content type."""
    extensions = {
        "application/fhir+json": ".json",
        "application/json": ".json",
        "application/fhir+ndjson": ".ndjson",
        "application/x-ndjson": ".ndjson",
    }
    return extensions.get(content_type, ".json")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for S3 key.

    Removes potentially dangerous characters and limits length.
    """
    # Allow only alphanumeric, dash, underscore, period
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    sanitized = "".join(c if c in safe_chars else "_" for c in filename)

    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    return sanitized or "upload"


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
