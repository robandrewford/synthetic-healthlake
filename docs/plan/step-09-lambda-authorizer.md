# Step 9: Lambda Authorizer Implementation

## Overview

JWT-based Lambda Authorizer for API Gateway. Validates tokens and extracts organization context for downstream Lambdas.

---

## api_authorizer/handler.py

```python
"""
Lambda Authorizer for API Gateway.

Validates JWT tokens and extracts organization context.
Supports:
- OAuth 2.0 Bearer tokens
- SMART on FHIR tokens
- Custom JWT tokens

SECURITY: This is the first line of defense for API access.
All tokens MUST contain organization_id claim.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
import boto3
import jwt
from jwt import PyJWKClient

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Cache JWKS client across Lambda invocations (warm start optimization)
_jwks_client: Optional[PyJWKClient] = None

# Cache for validated tokens (short TTL)
_token_cache: Dict[str, Dict[str, Any]] = {}
_cache_max_size = 100


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Token-based Lambda Authorizer.

    Args:
        event: Authorizer event from API Gateway
            - type: "TOKEN"
            - authorizationToken: "Bearer <token>"
            - methodArn: Resource ARN being accessed
        context: Lambda context

    Returns:
        IAM policy document allowing/denying access

    Raises:
        Exception("Unauthorized"): For any auth failure
    """

    logger.info("Processing authorization request")

    # Extract token from header
    token = extract_token(event)

    if not token:
        logger.warning("No token provided in request")
        raise Exception("Unauthorized")

    # Check cache first
    cached_claims = get_cached_claims(token)
    if cached_claims:
        logger.debug("Using cached token claims")
        return generate_allow_policy(cached_claims, event['methodArn'])

    try:
        # Validate token and extract claims
        claims = validate_token(token)

        # Verify required claims
        organization_id = extract_organization_id(claims)
        if not organization_id:
            logger.error("Token missing organization_id claim")
            raise Exception("Unauthorized")

        # Cache validated claims
        cache_claims(token, claims)

        # Generate allow policy with context
        return generate_allow_policy(claims, event['methodArn'])

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise Exception("Unauthorized")

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise Exception("Unauthorized")

    except Exception as e:
        logger.exception(f"Authorization error: {e}")
        raise Exception("Unauthorized")


def extract_token(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract Bearer token from Authorization header.

    Supports formats:
    - "Bearer <token>"
    - "<token>" (legacy)
    """
    auth_header = event.get('authorizationToken', '')

    if not auth_header:
        return None

    # Handle "Bearer <token>" format
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()

    # Handle raw token (legacy support)
    return auth_header.strip()


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token against JWKS endpoint.

    Returns:
        Decoded token claims

    Raises:
        jwt.InvalidTokenError: For invalid/expired tokens
    """
    global _jwks_client

    jwks_url = os.environ.get('JWKS_URL')

    if not jwks_url:
        # Fallback: validate with symmetric key (for testing)
        return validate_with_secret(token)

    # Initialize JWKS client (cached across invocations)
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)

    # Get signing key from JWKS
    signing_key = _jwks_client.get_signing_key_from_jwt(token)

    # Decode and validate token
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=['RS256', 'ES256'],
        audience=os.environ.get('API_AUDIENCE'),
        issuer=os.environ.get('TOKEN_ISSUER'),
        options={
            'verify_exp': True,
            'verify_iat': True,
            'verify_aud': bool(os.environ.get('API_AUDIENCE')),
            'verify_iss': bool(os.environ.get('TOKEN_ISSUER'))
        }
    )

    return claims


def validate_with_secret(token: str) -> Dict[str, Any]:
    """
    Validate token with symmetric secret (for development/testing).

    WARNING: Only use in dev environments.
    """
    secret = os.environ.get('JWT_SECRET')

    if not secret:
        raise jwt.InvalidTokenError("No JWKS_URL or JWT_SECRET configured")

    return jwt.decode(
        token,
        secret,
        algorithms=['HS256'],
        options={'verify_exp': True}
    )


def extract_organization_id(claims: Dict[str, Any]) -> Optional[str]:
    """
    Extract organization_id from token claims.

    Supports multiple claim names for compatibility:
    - organization_id (preferred)
    - org_id
    - org
    - tenant_id
    - https://healthtech.com/org_id (namespaced claim)
    """

    # Check standard claim names
    for claim_name in ['organization_id', 'org_id', 'org', 'tenant_id']:
        if claims.get(claim_name):
            return claims[claim_name]

    # Check namespaced claims (Auth0 style)
    for key, value in claims.items():
        if key.endswith('/org_id') or key.endswith('/organization_id'):
            return value

    return None


def generate_allow_policy(
    claims: Dict[str, Any],
    resource: str
) -> Dict[str, Any]:
    """
    Generate IAM policy document allowing API access.

    Includes organization context for downstream Lambdas.
    """

    # Extract principal ID (user identifier)
    principal_id = claims.get('sub', 'unknown')

    # Extract organization context
    organization_id = extract_organization_id(claims)
    organization_name = claims.get('organization_name', '')

    # Extract scopes
    scopes = extract_scopes(claims)

    # Build policy
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': 'Allow',
                'Resource': build_resource_arn(resource)
            }]
        },
        'context': {
            # These values are passed to downstream Lambdas
            'organization_id': organization_id,
            'organization_name': organization_name,
            'user_id': principal_id,
            'scopes': ','.join(scopes),
            'email': claims.get('email', ''),
            # Add any custom claims needed
            'token_type': claims.get('token_type', 'access')
        }
    }


def extract_scopes(claims: Dict[str, Any]) -> List[str]:
    """
    Extract scopes from token claims.

    Supports:
    - scope: "read write admin" (space-separated string)
    - scopes: ["read", "write"] (array)
    - permissions: ["read", "write"] (Auth0 style)
    """

    # Check 'scope' claim (space-separated string)
    scope_str = claims.get('scope', '')
    if scope_str:
        return [s.strip() for s in scope_str.split(' ') if s.strip()]

    # Check 'scopes' claim (array)
    scopes_list = claims.get('scopes', [])
    if scopes_list:
        return scopes_list

    # Check 'permissions' claim (Auth0)
    permissions = claims.get('permissions', [])
    if permissions:
        return permissions

    return []


def build_resource_arn(method_arn: str) -> str:
    """
    Build resource ARN pattern for policy.

    Allows access to all methods/paths under the same API.
    """
    # Parse method ARN
    # Format: arn:aws:execute-api:region:account:api-id/stage/method/resource
    parts = method_arn.split(':')

    if len(parts) >= 6:
        # Extract API Gateway parts
        api_parts = parts[5].split('/')
        if len(api_parts) >= 2:
            api_id = api_parts[0]
            stage = api_parts[1]
            # Allow all methods and paths
            return f"{':'.join(parts[:5])}:{api_id}/{stage}/*"

    # Fallback: return original ARN
    return method_arn


# Token cache functions
def get_cached_claims(token: str) -> Optional[Dict[str, Any]]:
    """Get claims from cache if not expired."""
    import time

    token_hash = hash(token)
    cached = _token_cache.get(token_hash)

    if cached:
        if cached['expires_at'] > time.time():
            return cached['claims']
        else:
            # Remove expired entry
            del _token_cache[token_hash]

    return None


def cache_claims(token: str, claims: Dict[str, Any]) -> None:
    """Cache validated claims for short TTL."""
    import time

    # Limit cache size
    if len(_token_cache) >= _cache_max_size:
        # Simple eviction: clear half the cache
        keys = list(_token_cache.keys())[:_cache_max_size // 2]
        for key in keys:
            del _token_cache[key]

    # Cache for 5 minutes or until token expires, whichever is shorter
    exp = claims.get('exp', time.time() + 300)
    cache_ttl = min(300, exp - time.time())

    _token_cache[hash(token)] = {
        'claims': claims,
        'expires_at': time.time() + cache_ttl
    }
```

---

## api_authorizer/requirements.txt

```
PyJWT>=2.8.0
cryptography>=41.0.0
boto3>=1.34.0
```

---

## Tests: tests/test_api_authorizer.py

```python
"""
Tests for Lambda Authorizer.
"""

import pytest
import jwt
import time
import os
from unittest.mock import patch, MagicMock

# Set environment variables before import
os.environ['JWT_SECRET'] = 'test-secret-key-for-testing-only'

from api_authorizer.handler import (
    lambda_handler,
    extract_token,
    extract_organization_id,
    extract_scopes,
    generate_allow_policy,
    build_resource_arn
)


@pytest.fixture
def valid_token():
    """Generate valid JWT token for testing."""
    payload = {
        'sub': 'user-123',
        'organization_id': 'org-456',
        'organization_name': 'Test Healthcare',
        'scope': 'patient.read patient.write',
        'email': 'user@test.com',
        'exp': time.time() + 3600,
        'iat': time.time()
    }
    return jwt.encode(payload, os.environ['JWT_SECRET'], algorithm='HS256')


@pytest.fixture
def expired_token():
    """Generate expired JWT token."""
    payload = {
        'sub': 'user-123',
        'organization_id': 'org-456',
        'exp': time.time() - 3600,  # Expired
        'iat': time.time() - 7200
    }
    return jwt.encode(payload, os.environ['JWT_SECRET'], algorithm='HS256')


@pytest.fixture
def token_without_org():
    """Generate token without organization_id."""
    payload = {
        'sub': 'user-123',
        'email': 'user@test.com',
        'exp': time.time() + 3600,
        'iat': time.time()
    }
    return jwt.encode(payload, os.environ['JWT_SECRET'], algorithm='HS256')


@pytest.fixture
def api_gateway_event(valid_token):
    """Create API Gateway authorizer event."""
    return {
        'type': 'TOKEN',
        'authorizationToken': f'Bearer {valid_token}',
        'methodArn': 'arn:aws:execute-api:us-east-1:123456789:api-id/dev/GET/v1/fhir/Patient'
    }


class TestExtractToken:
    """Tests for token extraction."""

    def test_extract_bearer_token(self):
        event = {'authorizationToken': 'Bearer abc123'}
        assert extract_token(event) == 'abc123'

    def test_extract_raw_token(self):
        event = {'authorizationToken': 'abc123'}
        assert extract_token(event) == 'abc123'

    def test_extract_empty_token(self):
        event = {'authorizationToken': ''}
        assert extract_token(event) is None

    def test_extract_missing_token(self):
        event = {}
        assert extract_token(event) is None

    def test_strip_whitespace(self):
        event = {'authorizationToken': 'Bearer   abc123  '}
        assert extract_token(event) == 'abc123'


class TestExtractOrganizationId:
    """Tests for organization ID extraction."""

    def test_extract_organization_id(self):
        claims = {'organization_id': 'org-123'}
        assert extract_organization_id(claims) == 'org-123'

    def test_extract_org_id(self):
        claims = {'org_id': 'org-123'}
        assert extract_organization_id(claims) == 'org-123'

    def test_extract_org(self):
        claims = {'org': 'org-123'}
        assert extract_organization_id(claims) == 'org-123'

    def test_extract_tenant_id(self):
        claims = {'tenant_id': 'org-123'}
        assert extract_organization_id(claims) == 'org-123'

    def test_extract_namespaced_claim(self):
        claims = {'https://healthtech.com/org_id': 'org-123'}
        assert extract_organization_id(claims) == 'org-123'

    def test_missing_organization_id(self):
        claims = {'sub': 'user-123', 'email': 'test@test.com'}
        assert extract_organization_id(claims) is None


class TestExtractScopes:
    """Tests for scope extraction."""

    def test_extract_space_separated_scope(self):
        claims = {'scope': 'read write admin'}
        assert extract_scopes(claims) == ['read', 'write', 'admin']

    def test_extract_scopes_array(self):
        claims = {'scopes': ['read', 'write']}
        assert extract_scopes(claims) == ['read', 'write']

    def test_extract_permissions(self):
        claims = {'permissions': ['patient:read', 'patient:write']}
        assert extract_scopes(claims) == ['patient:read', 'patient:write']

    def test_empty_scopes(self):
        claims = {}
        assert extract_scopes(claims) == []


class TestGenerateAllowPolicy:
    """Tests for policy generation."""

    def test_generates_valid_policy(self):
        claims = {
            'sub': 'user-123',
            'organization_id': 'org-456',
            'organization_name': 'Test Org',
            'scope': 'read write'
        }
        resource = 'arn:aws:execute-api:us-east-1:123:api/dev/GET/test'

        policy = generate_allow_policy(claims, resource)

        assert policy['principalId'] == 'user-123'
        assert policy['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert policy['context']['organization_id'] == 'org-456'
        assert policy['context']['scopes'] == 'read,write'


class TestLambdaHandler:
    """Integration tests for Lambda handler."""

    def test_valid_token_returns_allow_policy(self, api_gateway_event):
        result = lambda_handler(api_gateway_event, None)

        assert result['principalId'] == 'user-123'
        assert result['policyDocument']['Statement'][0]['Effect'] == 'Allow'
        assert result['context']['organization_id'] == 'org-456'

    def test_expired_token_raises_unauthorized(self, expired_token):
        event = {
            'type': 'TOKEN',
            'authorizationToken': f'Bearer {expired_token}',
            'methodArn': 'arn:aws:execute-api:us-east-1:123:api/dev/GET/test'
        }

        with pytest.raises(Exception, match="Unauthorized"):
            lambda_handler(event, None)

    def test_missing_org_raises_unauthorized(self, token_without_org):
        event = {
            'type': 'TOKEN',
            'authorizationToken': f'Bearer {token_without_org}',
            'methodArn': 'arn:aws:execute-api:us-east-1:123:api/dev/GET/test'
        }

        with pytest.raises(Exception, match="Unauthorized"):
            lambda_handler(event, None)

    def test_invalid_token_raises_unauthorized(self):
        event = {
            'type': 'TOKEN',
            'authorizationToken': 'Bearer invalid.token.here',
            'methodArn': 'arn:aws:execute-api:us-east-1:123:api/dev/GET/test'
        }

        with pytest.raises(Exception, match="Unauthorized"):
            lambda_handler(event, None)

    def test_missing_token_raises_unauthorized(self):
        event = {
            'type': 'TOKEN',
            'authorizationToken': '',
            'methodArn': 'arn:aws:execute-api:us-east-1:123:api/dev/GET/test'
        }

        with pytest.raises(Exception, match="Unauthorized"):
            lambda_handler(event, None)


class TestBuildResourceArn:
    """Tests for resource ARN building."""

    def test_builds_wildcard_arn(self):
        method_arn = 'arn:aws:execute-api:us-east-1:123456789:api-id/dev/GET/v1/fhir/Patient'
        result = build_resource_arn(method_arn)

        assert result == 'arn:aws:execute-api:us-east-1:123456789:api-id/dev/*'

    def test_handles_malformed_arn(self):
        method_arn = 'invalid-arn'
        result = build_resource_arn(method_arn)

        assert result == method_arn
```

---

## Running Tests

```bash
cd lambda_functions

# Install test dependencies
pip install pytest PyJWT cryptography

# Run authorizer tests
pytest tests/test_api_authorizer.py -v

# Run with coverage
pytest tests/test_api_authorizer.py --cov=api_authorizer --cov-report=term-missing
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWKS_URL` | Yes* | JWKS endpoint URL for public key retrieval |
| `TOKEN_ISSUER` | No | Expected token issuer (iss claim) |
| `API_AUDIENCE` | No | Expected audience (aud claim) |
| `JWT_SECRET` | Dev only | Symmetric secret for local testing |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

*Either `JWKS_URL` or `JWT_SECRET` must be set.

---

## Integration with Identity Providers

### Auth0

```bash
JWKS_URL=https://your-tenant.auth0.com/.well-known/jwks.json
TOKEN_ISSUER=https://your-tenant.auth0.com/
API_AUDIENCE=https://api.healthtech.com
```

### AWS Cognito

```bash
JWKS_URL=https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/jwks.json
TOKEN_ISSUER=https://cognito-idp.{region}.amazonaws.com/{userPoolId}
API_AUDIENCE={appClientId}
```

### SMART on FHIR

```bash
JWKS_URL={ehr_base_url}/.well-known/jwks.json
TOKEN_ISSUER={ehr_base_url}
API_AUDIENCE={client_id}
```
