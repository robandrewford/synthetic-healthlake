import json
import logging
from health_platform.utils.db import execute_query

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handle GET /patient/{id}
    """
    try:
        # 1. Parse Input
        path_params = event.get('pathParameters') or {}
        patient_id = path_params.get('patientId')
        
        if not patient_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing patientId in path parameters'})
            }
            
        logger.info(f"Fetching patient: {patient_id}")
        
        # 2. Query Snowflake
        # Note: In a real app we might use a dedicated connection pool or specific role
        sql = "SELECT RECORD_CONTENT FROM RAW.PATIENTS WHERE RECORD_CONTENT:id::string = %s LIMIT 1"
        results = execute_query(sql, (patient_id,))
        
        # 3. Handle Response
        if not results:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Patient not found'})
            }
            
        # Snowflake connector returns dicts, RECORD_CONTENT is already a JSON string if using json format? 
        # Or it might be a distinct object depending on connector settings.
        # But VARIANT comes back as a string from python connector usually unless converter is enabled.
        # Let's assume it comes back as a string or dict.
        
        record = results[0]['RECORD_CONTENT']
        
        # If it's a string, we might want to ensure it's valid JSON for the response, 
        # but the API Gateway will stringify the body anyway.
        # If record is a dict (parsed JSON), json.dumps handles it.
        # If record is a string (raw JSON), json.dumps escapes it, which we DON'T want if we want the client to receive JSON.
        # So we should check.
        
        response_body = record
        if isinstance(record, str):
            # It's already a JSON string, so we can load it to re-dump it safely 
            # OR pass it directly if we are careful. 
            # To be safe and ensure consistent formatting/headers:
            response_body = json.loads(record)
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Error fetching patient: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error'})
        }
