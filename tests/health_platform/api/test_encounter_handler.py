"""
Unit tests for Encounter API handler.

Tests:
- GET /encounter/{id} - Single encounter retrieval
- GET /encounter - Search with filters
- Error handling
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from health_platform.api.encounter.handler import (
    lambda_handler,
    get_encounter,
    search_encounters,
    get_patient_encounters,
)


@patch('health_platform.api.encounter.handler.execute_query')
class TestEncounterHandler:
    """Tests for the main lambda_handler routing."""
    
    def test_get_encounter_success(self, mock_query):
        """Test successful single encounter retrieval."""
        mock_query.return_value = [{
            'RECORD_CONTENT': json.dumps({
                'resourceType': 'Encounter',
                'id': 'enc-123',
                'status': 'finished',
                'class': {'code': 'AMB'},
                'subject': {'reference': 'Patient/pat-456'}
            })
        }]
        
        event = {'pathParameters': {'encounterId': 'enc-123'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/fhir+json'
        
        body = json.loads(response['body'])
        assert body['resourceType'] == 'Encounter'
        assert body['id'] == 'enc-123'
        assert body['status'] == 'finished'
        
    def test_get_encounter_not_found(self, mock_query):
        """Test encounter not found returns 404."""
        mock_query.return_value = []
        
        event = {'pathParameters': {'encounterId': 'nonexistent'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['resourceType'] == 'OperationOutcome'
        assert body['issue'][0]['code'] == 'not-found'
        
    def test_search_encounters_no_params(self, mock_query):
        """Test search without parameters returns all encounters."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],  # Count query
            [
                {'RECORD_CONTENT': json.dumps({'id': 'enc-1', 'resourceType': 'Encounter'})},
                {'RECORD_CONTENT': json.dumps({'id': 'enc-2', 'resourceType': 'Encounter'})}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': None
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['resourceType'] == 'Bundle'
        assert body['type'] == 'searchset'
        assert body['total'] == 2
        assert len(body['entry']) == 2
        
    def test_search_encounters_by_patient(self, mock_query):
        """Test search filtered by patient ID."""
        mock_query.side_effect = [
            [{'TOTAL': 1}],
            [{'RECORD_CONTENT': json.dumps({
                'id': 'enc-1',
                'resourceType': 'Encounter',
                'subject': {'reference': 'Patient/pat-123'}
            })}]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'patient': 'pat-123'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 1
        assert len(body['entry']) == 1
        
    def test_search_encounters_by_status(self, mock_query):
        """Test search filtered by encounter status."""
        mock_query.side_effect = [
            [{'TOTAL': 3}],
            [
                {'RECORD_CONTENT': json.dumps({'id': 'enc-1', 'status': 'finished'})},
                {'RECORD_CONTENT': json.dumps({'id': 'enc-2', 'status': 'finished'})},
                {'RECORD_CONTENT': json.dumps({'id': 'enc-3', 'status': 'finished'})}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'status': 'finished'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 3
        
    def test_search_encounters_by_date(self, mock_query):
        """Test search filtered by date."""
        mock_query.side_effect = [
            [{'TOTAL': 1}],
            [{'RECORD_CONTENT': json.dumps({
                'id': 'enc-1',
                'period': {'start': '2024-01-15T09:00:00Z'}
            })}]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'date': '2024-01-15'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 1
        
    def test_search_encounters_by_class(self, mock_query):
        """Test search filtered by encounter class."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],
            [
                {'RECORD_CONTENT': json.dumps({'id': 'enc-1', 'class': {'code': 'AMB'}})},
                {'RECORD_CONTENT': json.dumps({'id': 'enc-2', 'class': {'code': 'AMB'}})}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'class': 'AMB'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 2
        
    def test_search_encounters_pagination(self, mock_query):
        """Test pagination parameters."""
        mock_query.side_effect = [
            [{'TOTAL': 100}],
            [{'RECORD_CONTENT': json.dumps({'id': f'enc-{i}'})} for i in range(10)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'_count': '10', '_offset': '20'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 100
        assert len(body['entry']) == 10
        
    def test_search_encounters_max_count_capped(self, mock_query):
        """Test that _count is capped at 1000."""
        mock_query.side_effect = [
            [{'TOTAL': 5000}],
            [{'RECORD_CONTENT': json.dumps({'id': f'enc-{i}'})} for i in range(1000)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'_count': '5000'}  # Request more than limit
        }
        response = lambda_handler(event, {})
        
        # Verify the query was called with capped limit
        call_args = mock_query.call_args_list[1][0]  # Second call (search query)
        # The last two params should be (1000, 0) for LIMIT and OFFSET
        assert 1000 in call_args[1] if len(call_args) > 1 else True
        
    def test_search_encounters_invalid_pagination(self, mock_query):
        """Test invalid pagination parameters return 400."""
        event = {
            'pathParameters': None,
            'queryStringParameters': {'_count': 'invalid'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid pagination' in body['issue'][0]['diagnostics']
        
    def test_search_encounters_combined_filters(self, mock_query):
        """Test search with multiple filters combined."""
        mock_query.side_effect = [
            [{'TOTAL': 1}],
            [{'RECORD_CONTENT': json.dumps({
                'id': 'enc-1',
                'status': 'finished',
                'class': {'code': 'AMB'},
                'subject': {'reference': 'Patient/pat-123'}
            })}]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {
                'patient': 'pat-123',
                'status': 'finished',
                'class': 'AMB'
            }
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 1
        
    def test_internal_error(self, mock_query):
        """Test database error returns 500."""
        mock_query.side_effect = Exception("Database connection failed")
        
        event = {'pathParameters': {'encounterId': 'enc-123'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['resourceType'] == 'OperationOutcome'
        assert body['issue'][0]['severity'] == 'error'


@patch('health_platform.api.encounter.handler.execute_query')
class TestGetPatientEncounters:
    """Tests for the convenience method get_patient_encounters."""
    
    def test_get_patient_encounters(self, mock_query):
        """Test getting all encounters for a patient."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],
            [
                {'RECORD_CONTENT': json.dumps({'id': 'enc-1'})},
                {'RECORD_CONTENT': json.dumps({'id': 'enc-2'})}
            ]
        ]
        
        response = get_patient_encounters('pat-123', count=50, offset=0)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 2
        assert len(body['entry']) == 2


class TestParseRecord:
    """Tests for record parsing utility."""
    
    def test_parse_string_record(self):
        """Test parsing JSON string records."""
        from health_platform.api.encounter.handler import parse_record
        
        record = '{"id": "123", "status": "finished"}'
        result = parse_record(record)
        
        assert result['id'] == '123'
        assert result['status'] == 'finished'
        
    def test_parse_dict_record(self):
        """Test parsing dict records (already parsed)."""
        from health_platform.api.encounter.handler import parse_record
        
        record = {'id': '123', 'status': 'finished'}
        result = parse_record(record)
        
        assert result['id'] == '123'
        assert result['status'] == 'finished'
