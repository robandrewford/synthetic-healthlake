"""
Unit tests for Webhook Ingestion API handler.

Tests:
- POST /ingestion/fhir/Bundle - Bundle validation and storage
- GET /ingestion/jobs/{jobId} - Job status retrieval
- Error handling
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest


@patch("health_platform.ingestion.webhook.handler.sqs_client")
@patch("health_platform.ingestion.webhook.handler.s3_client")
class TestWebhookHandler:
    """Tests for the webhook lambda_handler."""

    def test_receive_bundle_success(self, mock_s3, mock_sqs):
        """Test successful bundle receipt."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        mock_s3.put_object.return_value = {}
        mock_sqs.send_message.return_value = {}

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
                {"resource": {"resourceType": "Encounter", "id": "e1"}},
            ],
        }

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": json.dumps(bundle),
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 202  # Accepted
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert body["status"] == "accepted"
        assert "jobId" in body
        assert body["resourceCount"] == {"Patient": 1, "Encounter": 1}

        # Verify S3 was called
        mock_s3.put_object.assert_called_once()

    def test_receive_bundle_empty_body(self, mock_s3, mock_sqs):
        """Test empty request body returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": "",
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "empty" in body["error"].lower()

    def test_receive_bundle_invalid_json(self, mock_s3, mock_sqs):
        """Test invalid JSON returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": "not valid json {{{",
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "json" in body["error"].lower()

    def test_receive_bundle_wrong_resource_type(self, mock_s3, mock_sqs):
        """Test non-Bundle resourceType returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": json.dumps({"resourceType": "Patient", "id": "p1"}),
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Bundle" in body["error"]

    def test_receive_bundle_invalid_type(self, mock_s3, mock_sqs):
        """Test invalid bundle type returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        bundle = {
            "resourceType": "Bundle",
            "type": "invalid-type",
            "entry": [{"resource": {"resourceType": "Patient"}}],
        }

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": json.dumps(bundle),
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "type" in body["error"].lower()

    def test_receive_bundle_empty_entries(self, mock_s3, mock_sqs):
        """Test bundle with no entries returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        bundle = {"resourceType": "Bundle", "type": "transaction", "entry": []}

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": json.dumps(bundle),
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "entries" in body["error"].lower()

    def test_receive_bundle_entry_missing_resource(self, mock_s3, mock_sqs):
        """Test entry without resource returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {"fullUrl": "urn:uuid:123"}  # No 'resource' field
            ],
        }

        event = {
            "httpMethod": "POST",
            "path": "/ingestion/fhir/Bundle",
            "body": json.dumps(bundle),
            "requestContext": {"requestId": "test-request-123"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "resource" in body["error"].lower()

    def test_receive_bundle_all_valid_types(self, mock_s3, mock_sqs):
        """Test all valid bundle types are accepted."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        mock_s3.put_object.return_value = {}
        mock_sqs.send_message.return_value = {}

        valid_types = ["transaction", "batch", "collection", "message", "document"]

        for bundle_type in valid_types:
            bundle = {
                "resourceType": "Bundle",
                "type": bundle_type,
                "entry": [{"resource": {"resourceType": "Patient", "id": "p1"}}],
            }

            event = {
                "httpMethod": "POST",
                "path": "/ingestion/fhir/Bundle",
                "body": json.dumps(bundle),
                "requestContext": {"requestId": f"test-{bundle_type}"},
            }

            response = lambda_handler(event, {})
            assert response["statusCode"] == 202, f"Failed for type: {bundle_type}"


@patch("health_platform.ingestion.webhook.handler.sqs_client")
@patch("health_platform.ingestion.webhook.handler.s3_client")
class TestJobStatus:
    """Tests for job status retrieval."""

    def test_get_job_status_found(self, mock_s3, mock_sqs):
        """Test getting status of existing job."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        mock_s3.head_object.return_value = {
            "ContentLength": 1024,
            "LastModified": datetime(2024, 1, 15, 10, 30, 0),
            "Metadata": {"entry_count": "5"},
        }

        event = {
            "httpMethod": "GET",
            "path": "/ingestion/jobs/job-20240115103000-abc12345",
            "pathParameters": {"jobId": "job-20240115103000-abc12345"},
            "requestContext": {"requestId": "test-request"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["jobId"] == "job-20240115103000-abc12345"
        assert body["status"] == "processing"
        assert body["metadata"]["size"] == 1024

    def test_get_job_status_not_found(self, mock_s3, mock_sqs):
        """Test getting status of non-existent job."""
        from botocore.exceptions import ClientError

        from health_platform.ingestion.webhook.handler import lambda_handler

        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        mock_s3.head_object.side_effect = ClientError(error_response, "HeadObject")
        mock_s3.exceptions.ClientError = ClientError

        event = {
            "httpMethod": "GET",
            "path": "/ingestion/jobs/job-nonexistent",
            "pathParameters": {"jobId": "job-nonexistent"},
            "requestContext": {"requestId": "test-request"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "not found" in body["error"].lower()

    def test_get_job_status_missing_id(self, mock_s3, mock_sqs):
        """Test missing job ID returns 400."""
        from health_platform.ingestion.webhook.handler import lambda_handler

        event = {
            "httpMethod": "GET",
            "path": "/ingestion/jobs/",
            "pathParameters": {},
            "requestContext": {"requestId": "test-request"},
        }

        response = lambda_handler(event, {})

        assert response["statusCode"] == 400


@patch("health_platform.ingestion.webhook.handler.sqs_client")
@patch("health_platform.ingestion.webhook.handler.s3_client")
class TestResourceCounting:
    """Tests for resource counting."""

    def test_count_multiple_resource_types(self, mock_s3, mock_sqs):
        """Test counting different resource types in bundle."""
        from health_platform.ingestion.webhook.handler import count_resources

        bundle = {
            "entry": [
                {"resource": {"resourceType": "Patient", "id": "p1"}},
                {"resource": {"resourceType": "Patient", "id": "p2"}},
                {"resource": {"resourceType": "Encounter", "id": "e1"}},
                {"resource": {"resourceType": "Observation", "id": "o1"}},
                {"resource": {"resourceType": "Observation", "id": "o2"}},
                {"resource": {"resourceType": "Observation", "id": "o3"}},
            ]
        }

        counts = count_resources(bundle)

        assert counts["Patient"] == 2
        assert counts["Encounter"] == 1
        assert counts["Observation"] == 3


class TestValidation:
    """Tests for bundle validation."""

    def test_parse_valid_bundle(self):
        """Test parsing valid bundle."""
        from health_platform.ingestion.webhook.handler import parse_bundle

        body = json.dumps(
            {
                "resourceType": "Bundle",
                "type": "transaction",
                "entry": [{"resource": {"resourceType": "Patient"}}],
            }
        )

        result = parse_bundle(body)

        assert result["resourceType"] == "Bundle"
        assert result["type"] == "transaction"

    def test_parse_bundle_validation_error(self):
        """Test validation error for invalid bundle."""
        from health_platform.ingestion.webhook.handler import (
            ValidationError,
            parse_bundle,
        )

        with pytest.raises(ValidationError):
            parse_bundle("")  # Empty body


class TestJobIdGeneration:
    """Tests for job ID generation."""

    def test_generate_job_id_format(self):
        """Test job ID format."""
        from health_platform.ingestion.webhook.handler import generate_job_id

        job_id = generate_job_id("test-request-123")

        assert job_id.startswith("job-")
        parts = job_id.split("-")
        assert len(parts) == 3
        # Second part should be timestamp (14 digits)
        assert len(parts[1]) == 14
        assert parts[1].isdigit()
        # Third part should be hash (8 chars)
        assert len(parts[2]) == 8

    def test_generate_job_id_uniqueness(self):
        """Test job IDs are unique for different requests."""
        from health_platform.ingestion.webhook.handler import generate_job_id

        job_id_1 = generate_job_id("request-1")
        job_id_2 = generate_job_id("request-2")

        # Hash portion should differ
        assert job_id_1.split("-")[2] != job_id_2.split("-")[2]
