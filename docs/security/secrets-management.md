# Secrets Management

This document describes how the Health Platform manages secrets using AWS Secrets Manager.

## Overview

The platform uses AWS Secrets Manager to securely store and retrieve sensitive credentials:

- **Snowflake database credentials** - Used by API Lambdas and dbt ECS tasks
- **Authentication secrets** - JWT signing keys and API key hashes for the authorizer

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         AWS Secrets Manager                              │
├─────────────────────────────────────────────────────────────────────────┤
│  health-platform/snowflake          health-platform/auth                │
│  ├── account                        ├── jwtSecret                       │
│  ├── user                           └── apiKeyHash                      │
│  ├── password                                                           │
│  ├── role                                                               │
│  ├── warehouse                                                          │
│  └── database                                                           │
└─────────────────────────────────────────────────────────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────┐              ┌─────────────────────┐
│   Lambda Functions  │              │   Authorizer Lambda │
│   (Patient, etc.)   │              │                     │
│                     │              │                     │
│ SNOWFLAKE_SECRET_ARN│              │   AUTH_SECRET_ARN   │
│ → Fetch at runtime  │              │   → Fetch at runtime│
└─────────────────────┘              └─────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ECS Fargate Tasks (dbt)                          │
│  Secrets injected as environment variables:                             │
│  DBT_SNOWFLAKE_ACCOUNT, DBT_SNOWFLAKE_USER, DBT_SNOWFLAKE_PASSWORD, etc│
└─────────────────────────────────────────────────────────────────────────┘
```

## Secrets Structure

### Snowflake Credentials (`health-platform/snowflake`)

```json
{
  "account": "your-account.us-east-1",
  "user": "service_user",
  "password": "secure-password",
  "role": "HEALTH_PLATFORM_ROLE",
  "warehouse": "COMPUTE_WH",
  "database": "HEALTH_PLATFORM_DB"
}
```

### Authentication (`health-platform/auth`)

```json
{
  "jwtSecret": "your-jwt-signing-secret-key",
  "apiKeyHash": "sha256-hash-of-api-key"
}
```

## CDK Implementation

The `PlatformSecrets` construct in `cdk/lib/constructs/secrets-construct.ts` provides:

### Creating Secrets (HealthPlatformStack)

```typescript
import { PlatformSecrets } from './constructs/secrets-construct';

const secrets = new PlatformSecrets(this, 'Secrets', {
  secretNamePrefix: 'health-platform',
  createSecrets: true,  // Creates secrets with placeholder values
});

// Grant Lambda access
secrets.grantSnowflakeRead(myLambdaFunction);
secrets.grantAuthRead(authorizerFunction);

// Get environment variables for Lambda
const env = secrets.getLambdaEnvironment();
// Returns: { SNOWFLAKE_SECRET_ARN: '...', SNOWFLAKE_SECRET_NAME: '...' }
```

### Referencing Existing Secrets (FhirOmopStack)

```typescript
const secrets = new PlatformSecrets(this, 'Secrets', {
  secretNamePrefix: 'health-platform',
  createSecrets: false,  // Reference existing secrets
});

// Get ECS secrets for container injection
const ecsSecrets = secrets.getEcsSnowflakeSecrets();
// Returns: { DBT_SNOWFLAKE_ACCOUNT: Secret, DBT_SNOWFLAKE_USER: Secret, ... }
```

## Lambda Runtime Usage

Lambda functions receive the secret ARN as an environment variable and must fetch the secret at runtime:

```python
import json
import boto3
import os

def get_snowflake_credentials():
    """Fetch Snowflake credentials from Secrets Manager."""
    client = boto3.client('secretsmanager')
    secret_arn = os.environ.get('SNOWFLAKE_SECRET_ARN')

    if not secret_arn:
        raise ValueError("SNOWFLAKE_SECRET_ARN not configured")

    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response['SecretString'])

# Usage
creds = get_snowflake_credentials()
connection = snowflake.connector.connect(
    account=creds['account'],
    user=creds['user'],
    password=creds['password'],
    role=creds['role'],
    warehouse=creds['warehouse'],
    database=creds['database'],
)
```

## ECS Task Usage

ECS tasks receive secrets directly as environment variables through AWS Fargate's native secret injection:

```yaml
# dbt profiles.yml uses env_var() to access injected secrets
health_platform:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('DBT_SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('DBT_SNOWFLAKE_USER') }}"
      password: "{{ env_var('DBT_SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('DBT_SNOWFLAKE_ROLE') }}"
      warehouse: "{{ env_var('DBT_SNOWFLAKE_WAREHOUSE') }}"
```

## Initial Setup

After deploying the CDK stack, update the secrets with real values:

### Using AWS CLI

```bash
# Update Snowflake credentials
aws secretsmanager put-secret-value \
  --secret-id health-platform/snowflake \
  --secret-string '{
    "account": "your-account.us-east-1",
    "user": "your_service_user",
    "password": "your_secure_password",
    "role": "HEALTH_PLATFORM_ROLE",
    "warehouse": "COMPUTE_WH",
    "database": "HEALTH_PLATFORM_DB"
  }'

# Update auth secret
aws secretsmanager put-secret-value \
  --secret-id health-platform/auth \
  --secret-string '{
    "jwtSecret": "your-64-char-jwt-secret-key",
    "apiKeyHash": ""
  }'
```

### Using AWS Console

1. Navigate to AWS Secrets Manager
2. Find `health-platform/snowflake`
3. Click "Retrieve secret value" → "Edit"
4. Update the JSON with real credentials
5. Repeat for `health-platform/auth`

## Security Best Practices

### Least Privilege Access

- Lambda functions only get access to the secrets they need
- API Lambdas: Snowflake credentials only
- Authorizer Lambda: Auth secrets only
- ECS tasks: Snowflake credentials for dbt

### VPC Endpoints

The `FhirOmopStack` includes a Secrets Manager VPC endpoint, allowing ECS tasks in private subnets to access secrets without traversing the public internet:

```typescript
'SecretsManager': ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER
```

### Automatic Rotation

Consider enabling automatic secret rotation for Snowflake credentials:

```typescript
// Add to PlatformSecrets construct if needed
this.snowflakeSecret.addRotationSchedule('Rotation', {
  rotationLambda: myRotationFunction,
  automaticallyAfter: cdk.Duration.days(30),
});
```

### Encryption

All secrets are encrypted at rest using AWS-managed keys by default. For additional security, you can specify a custom KMS key:

```typescript
const secrets = new PlatformSecrets(this, 'Secrets', {
  secretNamePrefix: 'health-platform',
  encryptionKeyArn: myKmsKey.keyArn,  // Optional: custom KMS key
});
```

## Troubleshooting

### Lambda Can't Access Secret

1. Verify the Lambda has `secretsmanager:GetSecretValue` permission
2. Check the secret ARN matches the environment variable
3. Ensure the secret exists in the correct region

### ECS Task Fails to Start

1. Check the execution role has `secretsmanager:GetSecretValue` permission
2. Verify the secret name/ARN is correct
3. Check CloudWatch logs for specific error messages

### Secret Not Found

1. Verify the secret was created by deploying `HealthPlatformStack` first
2. Check the secret name prefix matches (`health-platform`)
3. Ensure you're in the correct AWS region

## Related Documentation

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [ECS Secrets Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html)
- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
