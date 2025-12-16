"""
Unit tests for Observation API handler.

Tests:
- GET /observation/{id} - Single observation retrieval
- GET /observation - Search with filters (code, patient, date, category)
- Error handling
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from health_platform.api.observation.handler import (
    lambda_handler,
    get_observation,
    search_observations,
    get_patient_observations,
    get_vital_signs,
    get_lab_results,
)


@patch('health_platform.api.observation.handler.execute_query')
class TestObservationHandler:
    """Tests for the main lambda_handler routing."""
    
    def test_get_observation_success(self, mock_query):
        """Test successful single observation retrieval."""
        mock_query.return_value = [{
            'RECORD_CONTENT': json.dumps({
                'resourceType': 'Observation',
                'id': 'obs-123',
                'status': 'final',
                'code': {
                    'coding': [{'system': 'http://loinc.org', 'code': '2339-0', 'display': 'Glucose'}]
                },
                'subject': {'reference': 'Patient/pat-456'},
                'valueQuantity': {'value': 95, 'unit': 'mg/dL'}
            })
        }]
        
        event = {'pathParameters': {'observationId': 'obs-123'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['headers']['Content-Type'] == 'application/fhir+json'
        
        body = json.loads(response['body'])
        assert body['resourceType'] == 'Observation'
        assert body['id'] == 'obs-123'
        assert body['status'] == 'final'
        assert body['valueQuantity']['value'] == 95
        
    def test_get_observation_not_found(self, mock_query):
        """Test observation not found returns 404."""
        mock_query.return_value = []
        
        event = {'pathParameters': {'observationId': 'nonexistent'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['resourceType'] == 'OperationOutcome'
        assert body['issue'][0]['code'] == 'not-found'
        
    def test_search_observations_no_params(self, mock_query):
        """Test search without parameters returns all observations."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],  # Count query
            [
                {'RECORD_CONTENT': json.dumps({'id': 'obs-1', 'resourceType': 'Observation'})},
                {'RECORD_CONTENT': json.dumps({'id': 'obs-2', 'resourceType': 'Observation'})}
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
        
    def test_search_observations_by_patient(self, mock_query):
        """Test search filtered by patient ID."""
        mock_query.side_effect = [
            [{'TOTAL': 5}],
            [{'RECORD_CONTENT': json.dumps({
                'id': f'obs-{i}',
                'resourceType': 'Observation',
                'subject': {'reference': 'Patient/pat-123'}
            })} for i in range(5)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'patient': 'pat-123'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 5
        assert len(body['entry']) == 5
        
    def test_search_observations_by_single_code(self, mock_query):
        """Test search filtered by single LOINC code."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],
            [
                {'RECORD_CONTENT': json.dumps({
                    'id': 'obs-1',
                    'code': {'coding': [{'code': '2339-0'}]}
                })},
                {'RECORD_CONTENT': json.dumps({
                    'id': 'obs-2',
                    'code': {'coding': [{'code': '2339-0'}]}
                })}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'code': '2339-0'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 2
        
    def test_search_observations_by_multiple_codes(self, mock_query):
        """Test search filtered by multiple LOINC codes (comma-separated)."""
        mock_query.side_effect = [
            [{'TOTAL': 3}],
            [
                {'RECORD_CONTENT': json.dumps({'id': 'obs-1', 'code': {'coding': [{'code': '2339-0'}]}})},
                {'RECORD_CONTENT': json.dumps({'id': 'obs-2', 'code': {'coding': [{'code': '8867-4'}]}})},
                {'RECORD_CONTENT': json.dumps({'id': 'obs-3', 'code': {'coding': [{'code': '2339-0'}]}})}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'code': '2339-0,8867-4'}  # Glucose, Heart rate
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 3
        
    def test_search_observations_by_date(self, mock_query):
        """Test search filtered by date."""
        mock_query.side_effect = [
            [{'TOTAL': 1}],
            [{'RECORD_CONTENT': json.dumps({
                'id': 'obs-1',
                'effectiveDateTime': '2024-01-15T10:30:00Z'
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
        
    def test_search_observations_by_category_vital_signs(self, mock_query):
        """Test search filtered by vital-signs category."""
        mock_query.side_effect = [
            [{'TOTAL': 4}],
            [{'RECORD_CONTENT': json.dumps({
                'id': f'obs-{i}',
                'category': [{'coding': [{'code': 'vital-signs'}]}]
            })} for i in range(4)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'category': 'vital-signs'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 4
        
    def test_search_observations_by_category_laboratory(self, mock_query):
        """Test search filtered by laboratory category."""
        mock_query.side_effect = [
            [{'TOTAL': 10}],
            [{'RECORD_CONTENT': json.dumps({
                'id': f'obs-{i}',
                'category': [{'coding': [{'code': 'laboratory'}]}]
            })} for i in range(10)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'category': 'laboratory'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 10
        
    def test_search_observations_by_status(self, mock_query):
        """Test search filtered by observation status."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],
            [
                {'RECORD_CONTENT': json.dumps({'id': 'obs-1', 'status': 'final'})},
                {'RECORD_CONTENT': json.dumps({'id': 'obs-2', 'status': 'final'})}
            ]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'status': 'final'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 2
        
    def test_search_observations_pagination(self, mock_query):
        """Test pagination parameters."""
        mock_query.side_effect = [
            [{'TOTAL': 500}],
            [{'RECORD_CONTENT': json.dumps({'id': f'obs-{i}'})} for i in range(50)]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {'_count': '50', '_offset': '100'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 500
        assert len(body['entry']) == 50
        
    def test_search_observations_invalid_pagination(self, mock_query):
        """Test invalid pagination parameters return 400."""
        event = {
            'pathParameters': None,
            'queryStringParameters': {'_count': 'abc'}
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid pagination' in body['issue'][0]['diagnostics']
        
    def test_search_observations_combined_filters(self, mock_query):
        """Test search with multiple filters combined."""
        mock_query.side_effect = [
            [{'TOTAL': 1}],
            [{'RECORD_CONTENT': json.dumps({
                'id': 'obs-1',
                'status': 'final',
                'code': {'coding': [{'code': '2339-0'}]},
                'subject': {'reference': 'Patient/pat-123'},
                'category': [{'coding': [{'code': 'laboratory'}]}]
            })}]
        ]
        
        event = {
            'pathParameters': None,
            'queryStringParameters': {
                'patient': 'pat-123',
                'code': '2339-0',
                'category': 'laboratory',
                'status': 'final'
            }
        }
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 1
        
    def test_internal_error(self, mock_query):
        """Test database error returns 500."""
        mock_query.side_effect = Exception("Database connection failed")
        
        event = {'pathParameters': {'observationId': 'obs-123'}}
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['resourceType'] == 'OperationOutcome'
        assert body['issue'][0]['severity'] == 'error'


@patch('health_platform.api.observation.handler.execute_query')
class TestConvenienceMethods:
    """Tests for convenience methods."""
    
    def test_get_patient_observations(self, mock_query):
        """Test getting all observations for a patient."""
        mock_query.side_effect = [
            [{'TOTAL': 3}],
            [{'RECORD_CONTENT': json.dumps({'id': f'obs-{i}'})} for i in range(3)]
        ]
        
        response = get_patient_observations('pat-123', count=50)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 3
        
    def test_get_patient_observations_with_code(self, mock_query):
        """Test getting observations for a patient with code filter."""
        mock_query.side_effect = [
            [{'TOTAL': 2}],
            [{'RECORD_CONTENT': json.dumps({'id': f'obs-{i}'})} for i in range(2)]
        ]
        
        response = get_patient_observations('pat-123', code='2339-0')
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 2
        
    def test_get_vital_signs(self, mock_query):
        """Test getting vital signs for a patient."""
        mock_query.side_effect = [
            [{'TOTAL': 5}],
            [{'RECORD_CONTENT': json.dumps({
                'id': f'obs-{i}',
                'category': [{'coding': [{'code': 'vital-signs'}]}]
            })} for i in range(5)]
        ]
        
        response = get_vital_signs('pat-123')
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 5
        
    def test_get_lab_results(self, mock_query):
        """Test getting laboratory results for a patient."""
        mock_query.side_effect = [
            [{'TOTAL': 8}],
            [{'RECORD_CONTENT': json.dumps({
                'id': f'obs-{i}',
                'category': [{'coding': [{'code': 'laboratory'}]}]
            })} for i in range(8)]
        ]
        
        response = get_lab_results('pat-123')
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['total'] == 8


class TestParseRecord:
    """Tests for record parsing utility."""
    
    def test_parse_string_record(self):
        """Test parsing JSON string records."""
        from health_platform.api.observation.handler import parse_record
        
        record = '{"id": "obs-123", "status": "final", "valueQuantity": {"value": 95}}'
        result = parse_record(record)
        
        assert result['id'] == 'obs-123'
        assert result['status'] == 'final'
        assert result['valueQuantity']['value'] == 95
        
    def test_parse_dict_record(self):
        """Test parsing dict records (already parsed)."""
        from health_platform.api.observation.handler import parse_record
        
        record = {'id': 'obs-123', 'status': 'final'}
        result = parse_record(record)
        
        assert result['id'] == 'obs-123'
        assert result['status'] == 'final'
