# Step 8: Shared Utilities - Organization Scoping

## Overview

Core shared utilities enforcing Bezos Mandate: all data access must be organization-scoped with no cross-tenant leakage.

---

## shared/exceptions.py

```python
"""
Custom exceptions for API layer.
"""


class SecurityError(Exception):
    """
    Raised when data access violates organization boundaries.
    This is a Bezos Mandate violation and must be treated as critical.
    """
    pass


class AuthenticationError(Exception):
    """Raised when token validation fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks required scope/permission."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when requested resource doesn't exist."""
    pass


class ValidationError(Exception):
    """Raised when request payload is invalid."""
    pass


class RateLimitError(Exception):
    """Raised when rate limit exceeded."""
    pass
```

---

## shared/organization.py

```python
"""
Organization-scoped data access enforcement.

BEZOS MANDATE COMPLIANCE:
- Every query MUST include organization_id filter
- No cross-organization data access allowed
- Enforced at query layer, not just API layer
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
import hashlib
import logging

from .exceptions import SecurityError

logger = logging.getLogger(__name__)


@dataclass
class OrganizationContext:
    """
    Extracted from JWT token, passed to every data access call.
    
    This context MUST be present for all database operations.
    """
    organization_id: str
    organization_name: str
    scopes: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.organization_id:
            raise SecurityError("organization_id is required")
        
        if not self.organization_id.strip():
            raise SecurityError("organization_id cannot be empty")
    
    def has_scope(self, scope: str) -> bool:
        """Check if context has required scope."""
        return scope in self.scopes or 'admin' in self.scopes
    
    def require_scope(self, scope: str) -> None:
        """Raise if required scope is missing."""
        if not self.has_scope(scope):
            raise SecurityError(f"Missing required scope: {scope}")
    
    def to_log_context(self) -> Dict[str, str]:
        """Return sanitized context for logging."""
        return {
            'organization_id': self.organization_id,
            'user_id': self.user_id or 'anonymous',
            'request_id': self.request_id or 'unknown'
        }


class OrganizationScopedQuery:
    """
    Wrapper ensuring all Snowflake queries are organization-scoped.
    
    CRITICAL: This class enforces the Bezos Mandate at the query layer.
    All queries MUST reference organization_id in their WHERE clause.
    """
    
    # Keywords that indicate organization filtering
    ORG_FILTER_PATTERNS = [
        'organization_id',
        'org_id',
        'tenant_id'
    ]
    
    def __init__(self, connection, org_context: OrganizationContext):
        self.conn = connection
        self.org = org_context
        self._query_count = 0
    
    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute query with mandatory organization_id filter.
        
        Args:
            query: SQL query string (must reference organization_id)
            params: Query parameters (organization_id will be injected)
        
        Returns:
            List of result rows as dictionaries
        
        Raises:
            SecurityError: If query doesn't filter by organization_id
        """
        params = params or {}
        
        # SECURITY CHECK: Verify query includes organization filter
        if not self._has_org_filter(query):
            logger.error(
                "BEZOS MANDATE VIOLATION: Query missing organization_id filter",
                extra={
                    'query_preview': query[:200],
                    **self.org.to_log_context()
                }
            )
            raise SecurityError(
                "All queries MUST filter by organization_id. "
                "This is a Bezos Mandate violation."
            )
        
        # Inject organization_id into params
        params['organization_id'] = self.org.organization_id
        
        # Execute query
        cursor = self.conn.cursor()
        try:
            logger.debug(
                f"Executing org-scoped query",
                extra={
                    'query_preview': query[:100],
                    **self.org.to_log_context()
                }
            )
            
            cursor.execute(query, params)
            self._query_count += 1
            
            # Convert to list of dicts
            columns = [desc[0].lower() for desc in cursor.description or []]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.debug(
                f"Query returned {len(results)} rows",
                extra=self.org.to_log_context()
            )
            
            return results
            
        finally:
            cursor.close()
    
    def execute_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Execute query expecting single result.
        
        Returns:
            Single result dict, or None if no results
        """
        results = self.execute(query, params)
        return results[0] if results else None
    
    def _has_org_filter(self, query: str) -> bool:
        """
        Check if query includes organization filter.
        
        This is a safety check, not a security boundary.
        The actual security comes from parameterized queries.
        """
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in self.ORG_FILTER_PATTERNS)
    
    @property
    def query_count(self) -> int:
        """Number of queries executed in this session."""
        return self._query_count


def generate_deterministic_token(
    value: str,
    organization_id: str,
    salt: str
) -> str:
    """
    Generate deterministic token for cross-table joins.
    
    Same input always produces same output within organization scope.
    Different organizations get different tokens for same value.
    
    Args:
        value: The value to tokenize (e.g., MRN, SSN)
        organization_id: Organization scope
        salt: Additional salt (from secrets manager)
    
    Returns:
        64-character hex token
    """
    # Combine value with org-specific context
    combined = f"{organization_id}:{salt}:{value}"
    
    # SHA-256 hash
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
```

---

## shared/auth.py

```python
"""
Authentication utilities for extracting context from API Gateway events.
"""

from typing import Dict, Any, Optional
import logging

from .organization import OrganizationContext
from .exceptions import AuthenticationError, SecurityError

logger = logging.getLogger(__name__)


def extract_org_context(event: Dict[str, Any]) -> OrganizationContext:
    """
    Extract organization context from API Gateway authorizer.
    
    Args:
        event: API Gateway proxy event
    
    Returns:
        OrganizationContext populated from authorizer claims
    
    Raises:
        AuthenticationError: If authorizer context is missing
        SecurityError: If organization_id is missing
    """
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    
    # Check for authorizer context
    if not authorizer:
        logger.warning("No authorizer context in request")
        raise AuthenticationError("Missing authentication context")
    
    # Extract organization_id (required)
    organization_id = authorizer.get('organization_id')
    if not organization_id:
        logger.error("Token missing organization_id claim")
        raise SecurityError("Missing organization context")
    
    # Extract optional fields
    organization_name = authorizer.get('organization_name', '')
    user_id = authorizer.get('user_id') or authorizer.get('sub')
    scopes_str = authorizer.get('scopes', '')
    scopes = [s.strip() for s in scopes_str.split(',') if s.strip()]
    
    # Extract request ID for tracing
    request_id = request_context.get('requestId')
    
    return OrganizationContext(
        organization_id=organization_id,
        organization_name=organization_name,
        scopes=scopes,
        user_id=user_id,
        request_id=request_id
    )


def extract_path_parameter(event: Dict[str, Any], param_name: str) -> Optional[str]:
    """Extract path parameter from API Gateway event."""
    path_params = event.get('pathParameters') or {}
    return path_params.get(param_name)


def extract_query_parameters(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract query string parameters from API Gateway event."""
    return event.get('queryStringParameters') or {}


def extract_body(event: Dict[str, Any]) -> Optional[str]:
    """Extract request body from API Gateway event."""
    return event.get('body')
```

---

## shared/fhir_utils.py

```python
"""
FHIR resource serialization utilities.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal


class FHIREncoder(json.JSONEncoder):
    """JSON encoder handling FHIR data types."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def to_fhir_json(resource: Dict[str, Any]) -> str:
    """Serialize resource to FHIR JSON."""
    return json.dumps(resource, cls=FHIREncoder, separators=(',', ':'))


def create_bundle(
    resources: List[Dict[str, Any]],
    bundle_type: str = 'searchset',
    total: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create FHIR Bundle from list of resources.
    
    Args:
        resources: List of FHIR resources
        bundle_type: Bundle type (searchset, collection, etc.)
        total: Total count (for pagination)
    
    Returns:
        FHIR Bundle resource
    """
    bundle = {
        'resourceType': 'Bundle',
        'type': bundle_type,
        'entry': [
            {'resource': resource}
            for resource in resources
        ]
    }
    
    if total is not None:
        bundle['total'] = total
    else:
        bundle['total'] = len(resources)
    
    return bundle


def create_operation_outcome(
    severity: str,
    code: str,
    diagnostics: str
) -> Dict[str, Any]:
    """
    Create FHIR OperationOutcome for error responses.
    
    Args:
        severity: fatal | error | warning | information
        code: Error code (see FHIR spec)
        diagnostics: Human-readable error message
    
    Returns:
        FHIR OperationOutcome resource
    """
    return {
        'resourceType': 'OperationOutcome',
        'issue': [{
            'severity': severity,
            'code': code,
            'diagnostics': diagnostics
        }]
    }


def format_patient_resource(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format database row as FHIR Patient resource.
    
    Args:
        row: Database row with patient data
    
    Returns:
        FHIR Patient resource
    """
    patient = {
        'resourceType': 'Patient',
        'id': row.get('id') or row.get('patient_token')
    }
    
    # Add gender if present
    if row.get('gender'):
        patient['gender'] = row['gender']
    
    # Add birthDate if present
    birth_date = row.get('birth_date') or row.get('birthDate')
    if birth_date:
        if isinstance(birth_date, (date, datetime)):
            patient['birthDate'] = birth_date.isoformat()
        else:
            patient['birthDate'] = str(birth_date)
    
    # Add meta with lastUpdated
    updated_at = row.get('updated_at')
    if updated_at:
        if isinstance(updated_at, datetime):
            patient['meta'] = {'lastUpdated': updated_at.isoformat()}
    
    return patient


def format_encounter_resource(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format database row as FHIR Encounter resource."""
    encounter = {
        'resourceType': 'Encounter',
        'id': row.get('id') or row.get('encounter_token'),
        'status': row.get('status', 'unknown')
    }
    
    # Add subject reference
    patient_id = row.get('patient_id') or row.get('patient_token')
    if patient_id:
        encounter['subject'] = {'reference': f'Patient/{patient_id}'}
    
    # Add period
    start = row.get('period_start') or row.get('start_date')
    end = row.get('period_end') or row.get('end_date')
    if start or end:
        encounter['period'] = {}
        if start:
            encounter['period']['start'] = start.isoformat() if hasattr(start, 'isoformat') else str(start)
        if end:
            encounter['period']['end'] = end.isoformat() if hasattr(end, 'isoformat') else str(end)
    
    return encounter


def format_observation_resource(row: Dict[str, Any]) -> Dict[str, Any]:
    """Format database row as FHIR Observation resource."""
    observation = {
        'resourceType': 'Observation',
        'id': row.get('id') or row.get('observation_token'),
        'status': row.get('status', 'final')
    }
    
    # Add code
    code = row.get('code') or row.get('loinc_code')
    display = row.get('display') or row.get('code_display')
    if code:
        observation['code'] = {
            'coding': [{
                'system': 'http://loinc.org',
                'code': code,
                'display': display
            }]
        }
    
    # Add subject reference
    patient_id = row.get('patient_id') or row.get('patient_token')
    if patient_id:
        observation['subject'] = {'reference': f'Patient/{patient_id}'}
    
    # Add value
    value = row.get('value') or row.get('value_quantity')
    unit = row.get('unit') or row.get('value_unit')
    if value is not None:
        observation['valueQuantity'] = {
            'value': float(value) if isinstance(value, Decimal) else value,
            'unit': unit
        }
    
    return observation
```

---

## Tests: tests/test_organization_scope.py

```python
"""
Tests for organization-scoped data access.

These tests verify Bezos Mandate compliance:
- All queries must filter by organization_id
- No cross-organization data access
"""

import pytest
from unittest.mock import Mock, MagicMock

from shared.organization import (
    OrganizationContext,
    OrganizationScopedQuery,
    generate_deterministic_token
)
from shared.exceptions import SecurityError


class TestOrganizationContext:
    """Tests for OrganizationContext."""
    
    def test_create_valid_context(self):
        ctx = OrganizationContext(
            organization_id='org-123',
            organization_name='Test Org',
            scopes=['read', 'write'],
            user_id='user-456'
        )
        
        assert ctx.organization_id == 'org-123'
        assert ctx.organization_name == 'Test Org'
        assert ctx.scopes == ['read', 'write']
        assert ctx.user_id == 'user-456'
    
    def test_missing_org_id_raises_error(self):
        with pytest.raises(SecurityError, match="organization_id is required"):
            OrganizationContext(
                organization_id=None,
                organization_name='Test'
            )
    
    def test_empty_org_id_raises_error(self):
        with pytest.raises(SecurityError, match="cannot be empty"):
            OrganizationContext(
                organization_id='   ',
                organization_name='Test'
            )
    
    def test_has_scope_returns_true_for_matching_scope(self):
        ctx = OrganizationContext(
            organization_id='org-123',
            organization_name='Test',
            scopes=['patient.read', 'patient.write']
        )
        
        assert ctx.has_scope('patient.read') is True
        assert ctx.has_scope('patient.write') is True
        assert ctx.has_scope('admin.delete') is False
    
    def test_admin_scope_grants_all_access(self):
        ctx = OrganizationContext(
            organization_id='org-123',
            organization_name='Test',
            scopes=['admin']
        )
        
        assert ctx.has_scope('anything') is True
        assert ctx.has_scope('patient.read') is True
    
    def test_require_scope_raises_when_missing(self):
        ctx = OrganizationContext(
            organization_id='org-123',
            organization_name='Test',
            scopes=['read']
        )
        
        with pytest.raises(SecurityError, match="Missing required scope"):
            ctx.require_scope('write')


class TestOrganizationScopedQuery:
    """Tests for OrganizationScopedQuery."""
    
    @pytest.fixture
    def mock_connection(self):
        conn = Mock()
        cursor = MagicMock()
        cursor.description = [('id',), ('name',)]
        cursor.fetchall.return_value = [('1', 'Test')]
        conn.cursor.return_value = cursor
        return conn
    
    @pytest.fixture
    def org_context(self):
        return OrganizationContext(
            organization_id='org-123',
            organization_name='Test Org'
        )
    
    def test_query_with_org_filter_succeeds(self, mock_connection, org_context):
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        results = query.execute(
            "SELECT * FROM patients WHERE organization_id = %(organization_id)s",
            {}
        )
        
        assert len(results) == 1
        assert results[0]['id'] == '1'
    
    def test_query_without_org_filter_raises_error(self, mock_connection, org_context):
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        with pytest.raises(SecurityError, match="MUST filter by organization_id"):
            query.execute("SELECT * FROM patients WHERE id = '123'", {})
    
    def test_org_id_injected_into_params(self, mock_connection, org_context):
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        query.execute(
            "SELECT * FROM patients WHERE organization_id = %(organization_id)s",
            {'other_param': 'value'}
        )
        
        # Verify the cursor.execute was called with org_id in params
        call_args = mock_connection.cursor().execute.call_args
        params = call_args[0][1]
        assert params['organization_id'] == 'org-123'
        assert params['other_param'] == 'value'
    
    def test_execute_one_returns_single_result(self, mock_connection, org_context):
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        result = query.execute_one(
            "SELECT * FROM patients WHERE organization_id = %(organization_id)s LIMIT 1",
            {}
        )
        
        assert result is not None
        assert result['id'] == '1'
    
    def test_execute_one_returns_none_for_empty_result(self, mock_connection, org_context):
        mock_connection.cursor().fetchall.return_value = []
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        result = query.execute_one(
            "SELECT * FROM patients WHERE organization_id = %(organization_id)s AND id = 'nonexistent'",
            {}
        )
        
        assert result is None
    
    def test_query_count_increments(self, mock_connection, org_context):
        query = OrganizationScopedQuery(mock_connection, org_context)
        
        assert query.query_count == 0
        
        query.execute("SELECT * FROM t WHERE organization_id = %(organization_id)s", {})
        assert query.query_count == 1
        
        query.execute("SELECT * FROM t WHERE organization_id = %(organization_id)s", {})
        assert query.query_count == 2


class TestDeterministicToken:
    """Tests for deterministic token generation."""
    
    def test_same_input_same_output(self):
        token1 = generate_deterministic_token('MRN123', 'org-1', 'salt')
        token2 = generate_deterministic_token('MRN123', 'org-1', 'salt')
        
        assert token1 == token2
    
    def test_different_org_different_token(self):
        token1 = generate_deterministic_token('MRN123', 'org-1', 'salt')
        token2 = generate_deterministic_token('MRN123', 'org-2', 'salt')
        
        assert token1 != token2
    
    def test_different_value_different_token(self):
        token1 = generate_deterministic_token('MRN123', 'org-1', 'salt')
        token2 = generate_deterministic_token('MRN456', 'org-1', 'salt')
        
        assert token1 != token2
    
    def test_token_is_64_hex_chars(self):
        token = generate_deterministic_token('test', 'org', 'salt')
        
        assert len(token) == 64
        assert all(c in '0123456789abcdef' for c in token)
```

---

## Running Tests

```bash
cd lambda_functions

# Install test dependencies
pip install pytest pytest-mock

# Run organization scope tests
pytest tests/test_organization_scope.py -v

# Run with coverage
pytest tests/test_organization_scope.py --cov=shared --cov-report=term-missing
```
