"""
Unit tests for Presigned URL Upload API handler.

Tests the POST /ingestion/upload-url endpoint for generating
presigned S3 URLs for bulk FHIR data uploads.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestPresignedHandler:
    """Tests for presigned URL generation endpoint."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client for presigned URL generation."""
        with patch('health_platform.ingestion.presigned.handler.s3_client') as mock:
            mock.generate_presigned_url.return_value = 'https://s3.amazonaws.com/bucket/key?signature=xxx'
            yield mock
    
    @pytest.fixture
    def handler(self, mock_s3_client):
        """Import handler after mocking dependencies."""
        from health_platform.ingestion.presigned.handler import lambda_handler
        return lambda_handler
    
    def test_generate_upload_url_default_content_type(self, handler, mock_s3_client):
        """Test generating presigned URL with default content type."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': '{}',
            'requestContext': {'requestId': 'test-request-123'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert 'uploadId' in body
        assert body['uploadId'].startswith('upload-')
        assert 'uploadUrl' in body
        assert body['method'] == 'PUT'
        assert body['headers']['Content-Type'] == 'application/fhir+json'
        assert body['s3Bucket'] == 'healthtech-data-lake'
        assert 'uploads/' in body['s3Key']
        assert body['s3Key'].endswith('.json')
        assert body['expiresIn'] == 3600
        assert 'expiresAt' in body
        assert 'instructions' in body
    
    def test_generate_upload_url_ndjson(self, handler, mock_s3_client):
        """Test generating presigned URL for NDJSON content type."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': json.dumps({'contentType': 'application/fhir+ndjson'}),
            'requestContext': {'requestId': 'test-request-456'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert body['headers']['Content-Type'] == 'application/fhir+ndjson'
        assert body['s3Key'].endswith('.ndjson')
    
    def test_generate_upload_url_with_filename(self, handler, mock_s3_client):
        """Test generating presigned URL with custom filename."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': json.dumps({
                'contentType': 'application/json',
                'filename': 'patient_batch_2024.json'
            }),
            'requestContext': {'requestId': 'test-request-789'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        assert 'patient_batch_2024.json' in body['s3Key']
    
    def test_generate_upload_url_empty_body(self, handler, mock_s3_client):
        """Test generating presigned URL with empty request body."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': '',
            'requestContext': {'requestId': 'test-request-empty'}
        }
        
        response = handler(event, None)
        
        # Should succeed with defaults
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['headers']['Content-Type'] == 'application/fhir+json'
    
    def test_generate_upload_url_invalid_content_type(self, handler, mock_s3_client):
        """Test error handling for invalid content type."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': json.dumps({'contentType': 'text/plain'}),
            'requestContext': {'requestId': 'test-request-invalid'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'Invalid contentType' in body['error']
    
    def test_generate_upload_url_all_valid_content_types(self, handler, mock_s3_client):
        """Test all valid content types are accepted."""
        valid_types = [
            ('application/fhir+json', '.json'),
            ('application/json', '.json'),
            ('application/fhir+ndjson', '.ndjson'),
            ('application/x-ndjson', '.ndjson')
        ]
        
        for content_type, expected_ext in valid_types:
            event = {
                'httpMethod': 'POST',
                'path': '/ingestion/upload-url',
                'body': json.dumps({'contentType': content_type}),
                'requestContext': {'requestId': f'test-{content_type}'}
            }
            
            response = handler(event, None)
            
            assert response['statusCode'] == 200, f"Failed for {content_type}"
            body = json.loads(response['body'])
            assert body['s3Key'].endswith(expected_ext), f"Wrong extension for {content_type}"
    
    def test_unknown_endpoint(self, handler, mock_s3_client):
        """Test error handling for unknown endpoints."""
        event = {
            'httpMethod': 'GET',
            'path': '/ingestion/unknown',
            'body': '',
            'requestContext': {'requestId': 'test-unknown'}
        }
        
        response = handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Unknown endpoint' in body['error']
    
    def test_response_headers(self, handler, mock_s3_client):
        """Test response includes proper headers."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': '{}',
            'requestContext': {'requestId': 'test-headers-123'}
        }
        
        response = handler(event, None)
        
        assert response['headers']['Content-Type'] == 'application/json'
        assert response['headers']['X-Request-Id'] == 'test-headers-123'
        assert 'X-Upload-Id' in response['headers']
    
    def test_s3_client_called_correctly(self, handler, mock_s3_client):
        """Test S3 client is called with correct parameters."""
        event = {
            'httpMethod': 'POST',
            'path': '/ingestion/upload-url',
            'body': json.dumps({'contentType': 'application/fhir+json'}),
            'requestContext': {'requestId': 'test-s3-call'}
        }
        
        handler(event, None)
        
        # Verify generate_presigned_url was called
        mock_s3_client.generate_presigned_url.assert_called_once()
        
        call_args = mock_s3_client.generate_presigned_url.call_args
        assert call_args[0][0] == 'put_object'
        
        params = call_args[1]['Params']
        assert params['Bucket'] == 'healthtech-data-lake'
        assert 'incoming/fhir/uploads/' in params['Key']
        assert params['ContentType'] == 'application/fhir+json'
        assert 'upload_id' in params['Metadata']
        
        assert call_args[1]['ExpiresIn'] == 3600
        assert call_args[1]['HttpMethod'] == 'PUT'


class TestFilenameValidation:
    """Tests for filename sanitization."""
    
    @pytest.fixture
    def sanitize_filename(self):
        """Import sanitize_filename function."""
        from health_platform.ingestion.presigned.handler import sanitize_filename
        return sanitize_filename
    
    def test_sanitize_normal_filename(self, sanitize_filename):
        """Test sanitization of normal filenames."""
        assert sanitize_filename('data.json') == 'data.json'
        assert sanitize_filename('patient_batch_2024.ndjson') == 'patient_batch_2024.ndjson'
    
    def test_sanitize_special_characters(self, sanitize_filename):
        """Test removal of special characters."""
        assert sanitize_filename('data<script>.json') == 'data_script_.json'
        assert sanitize_filename('file with spaces.json') == 'file_with_spaces.json'
        assert sanitize_filename('../../../etc/passwd') == '.._.._.._.._etc_passwd'
    
    def test_sanitize_long_filename(self, sanitize_filename):
        """Test truncation of long filenames."""
        long_name = 'a' * 150 + '.json'
        result = sanitize_filename(long_name)
        assert len(result) <= 100
    
    def test_sanitize_empty_filename(self, sanitize_filename):
        """Test handling of empty filename."""
        assert sanitize_filename('') == 'upload'
        assert sanitize_filename('   ') == 'upload'


class TestContentTypeValidation:
    """Tests for content type validation."""
    
    @pytest.fixture
    def parse_request(self):
        """Import parse_request function."""
        from health_platform.ingestion.presigned.handler import parse_request
        return parse_request
    
    def test_parse_empty_body(self, parse_request):
        """Test parsing empty body."""
        result = parse_request('')
        assert result == {}
    
    def test_parse_invalid_json(self, parse_request):
        """Test parsing invalid JSON."""
        result = parse_request('not json')
        assert result == {}
    
    def test_parse_valid_content_type(self, parse_request):
        """Test parsing valid content type."""
        result = parse_request(json.dumps({'contentType': 'application/fhir+json'}))
        assert result['contentType'] == 'application/fhir+json'
    
    def test_parse_invalid_content_type(self, parse_request):
        """Test parsing invalid content type raises error."""
        from health_platform.ingestion.presigned.handler import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            parse_request(json.dumps({'contentType': 'application/xml'}))
        
        assert 'Invalid contentType' in str(exc_info.value)


class TestUploadIdGeneration:
    """Tests for upload ID generation."""
    
    @pytest.fixture
    def generate_upload_id(self):
        """Import generate_upload_id function."""
        from health_platform.ingestion.presigned.handler import generate_upload_id
        return generate_upload_id
    
    def test_upload_id_format(self, generate_upload_id):
        """Test upload ID has correct format."""
        upload_id = generate_upload_id()
        
        assert upload_id.startswith('upload-')
        parts = upload_id.split('-')
        assert len(parts) == 3
        
        # Second part should be timestamp (14 digits)
        timestamp_part = parts[1]
        assert len(timestamp_part) == 14
        assert timestamp_part.isdigit()
    
    def test_upload_id_uniqueness(self, generate_upload_id):
        """Test upload IDs are unique."""
        ids = [generate_upload_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestFileExtension:
    """Tests for file extension mapping."""
    
    @pytest.fixture
    def get_file_extension(self):
        """Import get_file_extension function."""
        from health_platform.ingestion.presigned.handler import get_file_extension
        return get_file_extension
    
    def test_json_extension(self, get_file_extension):
        """Test JSON content types get .json extension."""
        assert get_file_extension('application/fhir+json') == '.json'
        assert get_file_extension('application/json') == '.json'
    
    def test_ndjson_extension(self, get_file_extension):
        """Test NDJSON content types get .ndjson extension."""
        assert get_file_extension('application/fhir+ndjson') == '.ndjson'
        assert get_file_extension('application/x-ndjson') == '.ndjson'
    
    def test_unknown_extension(self, get_file_extension):
        """Test unknown content types default to .json."""
        assert get_file_extension('unknown/type') == '.json'
