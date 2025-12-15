# Step 10: FHIR API Implementation

## Overview

Data Access Service implementing FHIR-compliant endpoints with organization-scoped Snowflake queries.

---

## fhir_api/snowflake_client.py

```python
"""
Snowflake client with connection pooling and organization scoping.

BEZOS MANDATE: All queries go through OrganizationScopedQuery
to enforce data isolation.
"""

import os
import json
import logging
from contextlib import contextmanager
from typing import Generator, Optional

import boto3
import snowflake.connector
from snowflake.connector import SnowflakeConnection

# Import from shared (copied during build)
from shared.organization import OrganizationContext, OrganizationScopedQuery
from shared.exceptions import SecurityError

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """
    Snowflake connection manager for API Lambda functions.
    
    Features:
    - Lazy credential loading from Secrets Manager
    - Connection reuse across Lambda invocations (warm start)
    - Organization-scoped query execution
    """
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self._credentials: Optional[dict] = None
        self._connection: Optional[SnowflakeConnection] = None
    
    @property
    def credentials(self) -> dict:
        """
        Load Snowflake credentials from Secrets Manager.
        Cached for Lambda warm starts.
        """
        if self._credentials is None:
            secret_arn = os.environ.get('SNOWFLAKE_SECRET_ARN')
            
            if not secret_arn:
                raise SecurityError("SNOWFLAKE_SECRET_ARN not configured")
            
            logger.info("Loading Snowflake credentials from Secrets Manager")
            
            secret = self.secrets_client.get_secret_value(SecretId=secret_arn)
            self._credentials = json.loads(secret['SecretString'])
        
        return self._credentials
    
    def get_connection(self) -> SnowflakeConnection:
        """
        Get or create Snowflake connection.
        Reuses connection for Lambda warm starts.
        """
        if self._connection is None or self._connection.is_closed():
            logger.info("Creating new Snowflake connection")
            
            self._connection = snowflake.connector.connect(
                account=self.credentials['account'],
                user=self.credentials['user'],
                password=self.credentials['password'],
                warehouse=os.environ.get('SNOWFLAKE_WAREHOUSE', 'API_WH'),
                database=os.environ.get('SNOWFLAKE_DATABASE', 'HEALTHTECH'),
                schema=os.environ.get('SNOWFLAKE_SCHEMA', 'ANALYTICS'),
                role=os.environ.get('SNOWFLAKE_ROLE', 'API_READER'),
                # Connection settings for Lambda
                client_session_keep_alive=True,
                network_timeout=30,
                login_timeout=30
            )
        
        return self._connection
    
    @contextmanager
    def scoped_connection(
        self, 
        org_context: OrganizationContext
    ) -> Generator[OrganizationScopedQuery, None, None]:
        """
        Yield organization-scoped query executor.
        
        Args:
            org_context: Organization context from authorizer
        
        Yields:
            OrganizationScopedQuery for executing org-filtered queries
        """
        conn = self.get_connection()
        
        try:
            yield OrganizationScopedQuery(conn, org_context)
        except Exception as e:
            logger.error(
                f"Query error: {e}",
                extra=org_context.to_log_context()
            )
            raise
    
    def close(self) -> None:
        """Close connection (called on Lambda shutdown)."""
        if self._connection and not self._connection.is_closed():
            self._connection.close()
            self._connection = None


# Singleton instance for connection reuse
_client: Optional[SnowflakeClient] = None


def get_client() -> SnowflakeClient:
    """Get singleton Snowflake client."""
    global _client
    if _client is None:
        _client = SnowflakeClient()
    return _client
```

---

## fhir_api/patient.py

```python
"""
Patient resource API handlers.

Implements:
- GET /v1/fhir/Patient/{id}
- GET /v1/fhir/Patient (search)
"""

from typing import Optional, Dict, Any, List
import logging

from shared.organization import OrganizationContext
from shared.fhir_utils import format_patient_resource, create_bundle
from shared.exceptions import ResourceNotFoundError
from snowflake_client import get_client

logger = logging.getLogger(__name__)


def get_patient(
    patient_id: str,
    org_context: OrganizationContext
) -> Optional[Dict[str, Any]]:
    """
    Retrieve single patient by ID (token).
    
    Args:
        patient_id: Patient token (not PHI)
        org_context: Organization context
    
    Returns:
        FHIR Patient resource or None if not found
    """
    
    query = """
    SELECT 
        patient_token AS id,
        gender,
        birth_date,
        deceased_flag,
        created_at,
        updated_at
    FROM analytics.dim_patient
    WHERE patient_token = %(patient_id)s
      AND organization_id = %(organization_id)s
    """
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        row = db.execute_one(query, {'patient_id': patient_id})
    
    if not row:
        logger.info(
            f"Patient not found: {patient_id}",
            extra=org_context.to_log_context()
        )
        return None
    
    return format_patient_resource(row)


def search_patients(
    org_context: OrganizationContext,
    identifier: Optional[str] = None,
    gender: Optional[str] = None,
    birthdate: Optional[str] = None,
    name: Optional[str] = None,
    _count: int = 100,
    _offset: int = 0
) -> Dict[str, Any]:
    """
    Search patients with FHIR search parameters.
    
    Args:
        org_context: Organization context
        identifier: External identifier (MRN)
        gender: male | female | other | unknown
        birthdate: Birth date (YYYY-MM-DD)
        name: Name search (partial match)
        _count: Max results to return
        _offset: Pagination offset
    
    Returns:
        FHIR Bundle with matching patients
    """
    
    # Base query - always filtered by organization
    query = """
    SELECT 
        patient_token AS id,
        gender,
        birth_date,
        deceased_flag,
        created_at,
        updated_at
    FROM analytics.dim_patient
    WHERE organization_id = %(organization_id)s
    """
    
    params: Dict[str, Any] = {}
    
    # Add optional filters
    if identifier:
        query += " AND external_identifier = %(identifier)s"
        params['identifier'] = identifier
    
    if gender:
        query += " AND gender = %(gender)s"
        params['gender'] = gender.lower()
    
    if birthdate:
        query += " AND birth_date = %(birthdate)s"
        params['birthdate'] = birthdate
    
    if name:
        # Name search against de-identified index
        # Note: Full names are not in analytics schema
        query += " AND name_search_index ILIKE %(name_pattern)s"
        params['name_pattern'] = f"%{name}%"
    
    # Add ordering and pagination
    query += " ORDER BY updated_at DESC LIMIT %(limit)s OFFSET %(offset)s"
    params['limit'] = min(_count, 1000)  # Cap at 1000
    params['offset'] = _offset
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        results = db.execute(query, params)
    
    # Format as FHIR resources
    patients = [format_patient_resource(row) for row in results]
    
    logger.info(
        f"Patient search returned {len(patients)} results",
        extra=org_context.to_log_context()
    )
    
    return create_bundle(patients, bundle_type='searchset')
```

---

## fhir_api/encounter.py

```python
"""
Encounter resource API handlers.

Implements:
- GET /v1/fhir/Encounter/{id}
- GET /v1/fhir/Encounter (search)
- GET /v1/fhir/Patient/{id}/Encounter (patient's encounters)
"""

from typing import Optional, Dict, Any, List
import logging

from shared.organization import OrganizationContext
from shared.fhir_utils import format_encounter_resource, create_bundle
from snowflake_client import get_client

logger = logging.getLogger(__name__)


def get_encounter(
    encounter_id: str,
    org_context: OrganizationContext
) -> Optional[Dict[str, Any]]:
    """
    Retrieve single encounter by ID.
    
    Args:
        encounter_id: Encounter token
        org_context: Organization context
    
    Returns:
        FHIR Encounter resource or None
    """
    
    query = """
    SELECT 
        e.encounter_token AS id,
        e.patient_token AS patient_id,
        e.status,
        e.class_code,
        e.type_code,
        e.period_start,
        e.period_end,
        e.created_at,
        e.updated_at
    FROM analytics.fct_encounter e
    WHERE e.encounter_token = %(encounter_id)s
      AND e.organization_id = %(organization_id)s
    """
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        row = db.execute_one(query, {'encounter_id': encounter_id})
    
    if not row:
        return None
    
    return format_encounter_resource(row)


def search_encounters(
    org_context: OrganizationContext,
    patient: Optional[str] = None,
    status: Optional[str] = None,
    date: Optional[str] = None,
    _count: int = 100,
    _offset: int = 0
) -> Dict[str, Any]:
    """
    Search encounters with FHIR search parameters.
    
    Args:
        org_context: Organization context
        patient: Patient token
        status: Encounter status
        date: Encounter date (YYYY-MM-DD)
        _count: Max results
        _offset: Pagination offset
    
    Returns:
        FHIR Bundle with matching encounters
    """
    
    query = """
    SELECT 
        e.encounter_token AS id,
        e.patient_token AS patient_id,
        e.status,
        e.class_code,
        e.type_code,
        e.period_start,
        e.period_end,
        e.updated_at
    FROM analytics.fct_encounter e
    WHERE e.organization_id = %(organization_id)s
    """
    
    params: Dict[str, Any] = {}
    
    if patient:
        query += " AND e.patient_token = %(patient)s"
        params['patient'] = patient
    
    if status:
        query += " AND e.status = %(status)s"
        params['status'] = status
    
    if date:
        query += " AND DATE(e.period_start) = %(date)s"
        params['date'] = date
    
    query += " ORDER BY e.period_start DESC LIMIT %(limit)s OFFSET %(offset)s"
    params['limit'] = min(_count, 1000)
    params['offset'] = _offset
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        results = db.execute(query, params)
    
    encounters = [format_encounter_resource(row) for row in results]
    
    return create_bundle(encounters, bundle_type='searchset')


def get_patient_encounters(
    patient_id: str,
    org_context: OrganizationContext,
    _count: int = 100,
    _offset: int = 0
) -> Dict[str, Any]:
    """
    Get all encounters for a specific patient.
    
    Args:
        patient_id: Patient token
        org_context: Organization context
        _count: Max results
        _offset: Pagination offset
    
    Returns:
        FHIR Bundle with patient's encounters
    """
    return search_encounters(
        org_context=org_context,
        patient=patient_id,
        _count=_count,
        _offset=_offset
    )
```

---

## fhir_api/observation.py

```python
"""
Observation resource API handlers.

Implements:
- GET /v1/fhir/Observation/{id}
- GET /v1/fhir/Observation (search)
"""

from typing import Optional, Dict, Any, List
import logging

from shared.organization import OrganizationContext
from shared.fhir_utils import format_observation_resource, create_bundle
from snowflake_client import get_client

logger = logging.getLogger(__name__)


def get_observation(
    observation_id: str,
    org_context: OrganizationContext
) -> Optional[Dict[str, Any]]:
    """
    Retrieve single observation by ID.
    
    Args:
        observation_id: Observation token
        org_context: Organization context
    
    Returns:
        FHIR Observation resource or None
    """
    
    query = """
    SELECT 
        o.observation_token AS id,
        o.patient_token AS patient_id,
        o.encounter_token AS encounter_id,
        o.status,
        o.loinc_code AS code,
        o.code_display AS display,
        o.value_quantity AS value,
        o.value_unit AS unit,
        o.value_string,
        o.effective_datetime,
        o.updated_at
    FROM analytics.fct_observation o
    WHERE o.observation_token = %(observation_id)s
      AND o.organization_id = %(organization_id)s
    """
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        row = db.execute_one(query, {'observation_id': observation_id})
    
    if not row:
        return None
    
    return format_observation_resource(row)


def search_observations(
    org_context: OrganizationContext,
    patient: Optional[str] = None,
    code: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
    _count: int = 100,
    _offset: int = 0
) -> Dict[str, Any]:
    """
    Search observations with FHIR search parameters.
    
    Args:
        org_context: Organization context
        patient: Patient token
        code: LOINC code
        date: Observation date (YYYY-MM-DD)
        category: Observation category
        _count: Max results
        _offset: Pagination offset
    
    Returns:
        FHIR Bundle with matching observations
    """
    
    query = """
    SELECT 
        o.observation_token AS id,
        o.patient_token AS patient_id,
        o.encounter_token AS encounter_id,
        o.status,
        o.loinc_code AS code,
        o.code_display AS display,
        o.value_quantity AS value,
        o.value_unit AS unit,
        o.value_string,
        o.effective_datetime,
        o.updated_at
    FROM analytics.fct_observation o
    WHERE o.organization_id = %(organization_id)s
    """
    
    params: Dict[str, Any] = {}
    
    if patient:
        query += " AND o.patient_token = %(patient)s"
        params['patient'] = patient
    
    if code:
        # Support single code or comma-separated list
        codes = [c.strip() for c in code.split(',')]
        if len(codes) == 1:
            query += " AND o.loinc_code = %(code)s"
            params['code'] = codes[0]
        else:
            query += " AND o.loinc_code IN %(codes)s"
            params['codes'] = tuple(codes)
    
    if date:
        query += " AND DATE(o.effective_datetime) = %(date)s"
        params['date'] = date
    
    if category:
        query += " AND o.category = %(category)s"
        params['category'] = category
    
    query += " ORDER BY o.effective_datetime DESC LIMIT %(limit)s OFFSET %(offset)s"
    params['limit'] = min(_count, 1000)
    params['offset'] = _offset
    
    client = get_client()
    with client.scoped_connection(org_context) as db:
        results = db.execute(query, params)
    
    observations = [format_observation_resource(row) for row in results]
    
    logger.info(
        f"Observation search returned {len(observations)} results",
        extra=org_context.to_log_context()
    )
    
    return create_bundle(observations, bundle_type='searchset')
```

---

## fhir_api/handler.py

```python
"""
FHIR API Lambda handler.

Routes requests to appropriate resource handlers.
Implements API Gateway proxy integration.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from shared.auth import (
    extract_org_context,
    extract_path_parameter,
    extract_query_parameters
)
from shared.fhir_utils import create_operation_outcome, to_fhir_json
from shared.exceptions import (
    SecurityError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError
)

import patient
import encounter
import observation

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    API Gateway proxy integration handler.
    
    Routes:
        GET /v1/fhir/Patient/{id} -> patient.get_patient
        GET /v1/fhir/Patient -> patient.search_patients
        GET /v1/fhir/Encounter/{id} -> encounter.get_encounter
        GET /v1/fhir/Encounter -> encounter.search_encounters
        GET /v1/fhir/Observation/{id} -> observation.get_observation
        GET /v1/fhir/Observation -> observation.search_observations
    """
    
    # Extract request details
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    path_params = event.get('pathParameters') or {}
    query_params = extract_query_parameters(event)
    
    request_id = event.get('requestContext', {}).get('requestId', 'unknown')
    
    logger.info(f"Processing {http_method} {path}", extra={'request_id': request_id})
    
    try:
        # Extract organization context from authorizer
        org_context = extract_org_context(event)
        
        # Route to appropriate handler
        result = route_request(
            http_method=http_method,
            path=path,
            path_params=path_params,
            query_params=query_params,
            org_context=org_context
        )
        
        if result is None:
            return error_response(404, 'not-found', 'Resource not found', request_id)
        
        return success_response(200, result, request_id)
    
    except AuthenticationError as e:
        logger.warning(f"Authentication error: {e}")
        return error_response(401, 'login', str(e), request_id)
    
    except SecurityError as e:
        logger.error(f"Security error: {e}")
        return error_response(403, 'forbidden', str(e), request_id)
    
    except ResourceNotFoundError as e:
        return error_response(404, 'not-found', str(e), request_id)
    
    except ValidationError as e:
        return error_response(400, 'invalid', str(e), request_id)
    
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        return error_response(500, 'exception', 'Internal server error', request_id)


def route_request(
    http_method: str,
    path: str,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    org_context: Any
) -> Optional[Dict[str, Any]]:
    """
    Route request to appropriate handler based on path.
    """
    
    # Normalize path
    path = path.rstrip('/')
    
    # Extract pagination params
    _count = int(query_params.get('_count', 100))
    _offset = int(query_params.get('_offset', 0))
    
    # Patient routes
    if '/Patient' in path:
        resource_id = path_params.get('id')
        
        if http_method == 'GET':
            if resource_id:
                # GET /v1/fhir/Patient/{id}
                return patient.get_patient(resource_id, org_context)
            else:
                # GET /v1/fhir/Patient (search)
                return patient.search_patients(
                    org_context=org_context,
                    identifier=query_params.get('identifier'),
                    gender=query_params.get('gender'),
                    birthdate=query_params.get('birthdate'),
                    name=query_params.get('name'),
                    _count=_count,
                    _offset=_offset
                )
    
    # Encounter routes
    elif '/Encounter' in path:
        resource_id = path_params.get('id')
        
        if http_method == 'GET':
            if resource_id:
                # GET /v1/fhir/Encounter/{id}
                return encounter.get_encounter(resource_id, org_context)
            else:
                # GET /v1/fhir/Encounter (search)
                return encounter.search_encounters(
                    org_context=org_context,
                    patient=query_params.get('patient'),
                    status=query_params.get('status'),
                    date=query_params.get('date'),
                    _count=_count,
                    _offset=_offset
                )
    
    # Observation routes
    elif '/Observation' in path:
        resource_id = path_params.get('id')
        
        if http_method == 'GET':
            if resource_id:
                # GET /v1/fhir/Observation/{id}
                return observation.get_observation(resource_id, org_context)
            else:
                # GET /v1/fhir/Observation (search)
                return observation.search_observations(
                    org_context=org_context,
                    patient=query_params.get('patient'),
                    code=query_params.get('code'),
                    date=query_params.get('date'),
                    category=query_params.get('category'),
                    _count=_count,
                    _offset=_offset
                )
    
    # Unknown route
    raise ValidationError(f"Unknown endpoint: {path}")


def success_response(
    status_code: int,
    body: Dict[str, Any],
    request_id: str
) -> Dict[str, Any]:
    """Format successful API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/fhir+json',
            'X-Request-Id': request_id,
            'Cache-Control': 'no-cache, no-store, must-revalidate'
        },
        'body': to_fhir_json(body)
    }


def error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str
) -> Dict[str, Any]:
    """Format error API response as FHIR OperationOutcome."""
    
    severity = 'error' if status_code >= 400 else 'warning'
    outcome = create_operation_outcome(severity, code, message)
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/fhir+json',
            'X-Request-Id': request_id
        },
        'body': to_fhir_json(outcome)
    }
```

---

## fhir_api/requirements.txt

```
snowflake-connector-python>=3.6.0
boto3>=1.34.0
```

---

## Running Tests

```bash
cd lambda_functions

# Install dependencies
pip install pytest pytest-mock snowflake-connector-python boto3

# Run FHIR API tests
pytest tests/test_fhir_api.py -v
```
