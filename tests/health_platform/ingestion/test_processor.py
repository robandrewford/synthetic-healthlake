import os

import boto3
import pytest
from moto import mock_aws

from health_platform.ingestion.processor.handler import lambda_handler
from health_platform.ingestion.processor.validator import (
    ValidationError,
    validate_ndjson,
)


class TestValidator:
    def test_valid_ndjson(self):
        content = '{"resourceType": "Patient", "id": "1"}\n{"resourceType": "Encounter", "id": "2"}'
        result = validate_ndjson(content)
        assert len(result) == 2
        assert result[0]["resourceType"] == "Patient"

    def test_invalid_json(self):
        content = '{"resourceType": "Patient"}\nbad_json'
        with pytest.raises(ValidationError) as e:
            validate_ndjson(content)
        assert "Invalid JSON" in str(e.value)

    def test_missing_resource_type(self):
        content = '{"id": "1"}'
        with pytest.raises(ValidationError) as e:
            validate_ndjson(content)
        assert "Missing 'resourceType'" in str(e.value)


@mock_aws
class TestHandler:
    def setup_method(self, method):
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.bucket = "test-bucket"
        self.s3.create_bucket(Bucket=self.bucket)

    def test_handler_success(self):
        # inputs
        key = "landing/test.ndjson"
        content = '{"resourceType": "Patient", "id": "1"}'
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=content)

        event = {"Records": [{"s3": {"bucket": {"name": self.bucket}, "object": {"key": key}}}]}

        # set env var
        os.environ["PROCESSED_PREFIX"] = "processed/"

        # execute
        response = lambda_handler(event, {})
        assert response["statusCode"] == 200

        # verify output
        dest_key = "processed/test.ndjson"
        response = self.s3.get_object(Bucket=self.bucket, Key=dest_key)
        out_content = response["Body"].read().decode("utf-8")
        assert "resourceType" in out_content

    def test_handler_validation_failure(self):
        # inputs
        key = "landing/bad.ndjson"
        content = '{"id": "1"}'  # Missing resourceType
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=content)

        event = {"Records": [{"s3": {"bucket": {"name": self.bucket}, "object": {"key": key}}}]}

        # execute
        with pytest.raises(ValidationError):
            lambda_handler(event, {})
