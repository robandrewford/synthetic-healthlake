# Secrets Management

This document describes how the Health Platform manages secrets using AWS Secrets Manager.

## Overview

The platform uses AWS Secrets Manager to securely store and retrieve sensitive credentials:

- **Snowflake database credentials** - Used by API Lambdas and dbt ECS tasks
- **Authentication secrets** - JWT signing keys and API key hashes for the authorizer

## Environment Variable Naming Convention

All environment variables follow the pattern: `{PROJECT}_{SERVICE}_{OBJECT}`

See [Environment Variable Naming Convention](../development/env-variable-naming-convention.md) for the full specification.

### Snowflake Variables (HP_SNF_*)

| Variable | Description |
|----------|-------------|
| `HP_SNF_ACCT` | Account locator (e.g., xy12345.us-east-1) |
| `HP_SNF_USER` | Service account username |
| `HP_SNF_PASS` | Service account password |
| `HP_SNF_ROLE` | Default role to assume |
| `HP_SNF_WH` | Compute warehouse name |
| `HP_SNF_DB` | Default database |
| `HP_SNF_SCHEMA` | Default schema |

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
│  HP_SNF_ACCT, HP_SNF_USER, HP_SNF_PASS, HP_SNF_ROLE, HP_SNF_WH, etc.   │
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
// Returns: { HP_SNF_ACCT: Secret, HP_SNF_USER: Secret, ... }
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
      account: "{{ env_var('HP_SNF_ACCT') }}"
      user: "{{ env_var('HP_SNF_USER') }}"
      password: "{{ env_var('HP_SNF_PASS') }}"
      role: "{{ env_var('HP_SNF_ROLE') }}"
      warehouse: "{{ env_var('HP_SNF_WH') }}"
      database: "{{ env_var('HP_SNF_DB') }}"
```

## Local Development

For local development, use one of these approaches:

### Option 1: direnv (Recommended)

```bash
# One-time setup
brew install direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
source ~/.zshrc

# In the project directory
cp .env.example .env
# Edit .env with your credentials
direnv allow .
```

### Option 2: Manual Environment Loading

```bash
# Load environment variables
source scripts/env-load.sh

# Run dbt commands
./scripts/run-dbt.sh debug
./scripts/run-dbt.sh run
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

### Local Environment Issues

1. Verify `.env` file exists and has correct values
2. If using direnv, run `direnv allow .` after changes
3. Check environment with: `echo $HP_SNF_ACCT`

## Related Documentation

- [Environment Variable Naming Convention](../development/env-variable-naming-convention.md)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [ECS Secrets Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html)
- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
