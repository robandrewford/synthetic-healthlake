import json
import pytest
from unittest.mock import patch, MagicMock
from health_platform.api.patient.handler import lambda_handler

@patch('health_platform.api.patient.handler.execute_query')
class TestPatientHandler:
    
    def test_get_patient_success(self, mock_query):
        # Setup
        mock_query.return_value = [{'RECORD_CONTENT': '{"id": "123", "name": "Test"}'}]
        event = {'pathParameters': {'patientId': '123'}}
        
        # Execute
        response = lambda_handler(event, {})
        
        # Verify
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['id'] == '123'
        assert body['name'] == 'Test'
        mock_query.assert_called_once()
        
    def test_get_patient_not_found(self, mock_query):
        # Setup
        mock_query.return_value = []
        event = {'pathParameters': {'patientId': '999'}}
        
        # Execute
        response = lambda_handler(event, {})
        
        # Verify
        assert response['statusCode'] == 404
        assert 'not found' in response['body']
        
    def test_missing_id(self, mock_query):
        # Setup
        event = {'pathParameters': {}}
        
        # Execute
        response = lambda_handler(event, {})
        
        # Verify
        assert response['statusCode'] == 400
        assert 'Missing patientId' in response['body']
        
    def test_internal_error(self, mock_query):
        # Setup
        mock_query.side_effect = Exception("DB Error")
        event = {'pathParameters': {'patientId': '123'}}
        
        # Execute
        response = lambda_handler(event, {})
        
        # Verify
        assert response['statusCode'] == 500
        assert 'Internal Server Error' in response['body']
