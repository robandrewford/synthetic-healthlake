# Environment Variable Naming Convention Specification

## Purpose

This specification defines a consistent, self-documenting naming convention for environment variables across all services, tools, and deployment contexts. The goal is **self-evident identification** without requiring a data dictionary.

## Pattern Structure

```text
{PROJECT}_{SERVICE}_{OBJECT}
```

| Segment | Description | Max Length | Case |
|---------|-------------|------------|------|
| `PROJECT` | Organization/project identifier | 2-4 chars | UPPER |
| `SERVICE` | Technology or service abbreviation | 2-4 chars | UPPER |
| `OBJECT` | The specific configuration item | 2-8 chars | UPPER |

- **Separator:** Underscore (`_`)
- **Total recommended length:** ≤20 characters

## Segment Definitions

### 1. PROJECT Prefix

The project prefix identifies the owning organization or system. Choose a memorable abbreviation of 2-4 characters.

| Full Name | Abbreviation | Rationale |
|-----------|--------------|-----------|
| Health Platform | `HP` | First letters, common pattern |
| Synthetic HealthLake | `SHL` | Acronym |
| Acme Corporation | `ACME` | Brand (≤4 chars OK) |

- **Rule:** If company name > 7 characters, abbreviate to ≤4 characters using:
  - First letters of each word (acronym)
  - Consonant compression (remove vowels)
  - Industry-standard abbreviation

### 2. SERVICE Abbreviation

The service segment identifies the technology or cloud provider.

| Service | Abbreviation | Notes |
|---------|--------------|-------|
| Snowflake | `SNF` | 3-char consonant compression |
| Amazon Web Services | `AWS` | Industry standard |
| Google Cloud Platform | `GCP` | Industry standard |
| Microsoft Azure | `AZ` | Common abbreviation |
| dbt (data build tool) | `DBT` | Already short |
| PostgreSQL | `PG` | Common abbreviation |
| Redis | `RDS` | 3-char |
| Kubernetes | `K8S` | Industry standard |
| Docker | `DKR` | 3-char consonant |

- **Rule:** Use industry-standard abbreviations where they exist; otherwise use 2-4 char consonant compression.

### 3. OBJECT Identifier

The object identifies the specific configuration item within the service.

| Object Type | Abbreviation | Full Name |
|-------------|--------------|-----------|
| `ACCT` | Account | Account identifier/locator |
| `USER` | User | Username |
| `PASS` | Password | Password or secret |
| `ROLE` | Role | IAM/RBAC role |
| `WH` | Warehouse | Compute warehouse |
| `DB` | Database | Database name |
| `SCHEMA` | Schema | Schema name |
| `REGION` | Region | Cloud region |
| `PROFILE` | Profile | Named profile |
| `HOST` | Host | Hostname/endpoint |
| `PORT` | Port | Port number |
| `KEY` | Key | API key or access key |
| `SECRET` | Secret | Secret key |
| `ARN` | ARN | AWS Resource Name |
| `BUCKET` | Bucket | S3/GCS bucket name |

- **Rule:** Object abbreviations should be 2-8 characters. Use common database/cloud terminology. Avoid ambiguous abbreviations.

## Construction Algorithm

```text
1. Identify the PROJECT prefix (2-4 uppercase chars)
2. Identify the SERVICE being configured (2-4 uppercase chars)
3. Identify the OBJECT type (2-8 uppercase chars)
4. Concatenate with underscores: PROJECT_SERVICE_OBJECT
5. Verify total length ≤ 20 characters
6. Verify no collision with existing variables
```

## Examples

### Snowflake Configuration

```bash
HP_SNF_ACCT=xy12345.us-east-1     # Account locator
HP_SNF_USER=service_user           # Service account username
HP_SNF_PASS=secure_password        # Password
HP_SNF_ROLE=ANALYST                # Role to assume
HP_SNF_WH=COMPUTE_WH               # Warehouse name
HP_SNF_DB=HEALTH_PLATFORM_DB       # Database name
HP_SNF_SCHEMA=ANALYTICS            # Default schema
```

### AWS Configuration

```bash
HP_AWS_PROFILE=health-platform     # Named profile
HP_AWS_REGION=us-east-1            # Default region
HP_AWS_KEY=AKIA...                 # Access key ID
HP_AWS_SECRET=...                  # Secret access key
HP_AWS_BUCKET=hp-data-bucket       # S3 bucket
HP_AWS_ARN=arn:aws:...             # Resource ARN
```

### dbt Configuration

```bash
HP_DBT_TARGET=dev                  # dbt target environment
HP_DBT_THREADS=4                   # Parallelism
HP_DBT_PROFILE=health_platform     # Profile name
```

## Anti-Patterns (Avoid)

| Bad Example | Problem | Good Example |
|-------------|---------|--------------|
| `SNOWFLAKE_ACCOUNT` | No project prefix | `HP_SNF_ACCT` |
| `DB_USER` | Ambiguous service | `HP_SNF_USER` |
| `HP_SNOWFLAKE_ACCOUNT` | Service too long | `HP_SNF_ACCT` |
| `HP_S_A` | Too abbreviated | `HP_SNF_ACCT` |
| `healthplatform_snowflake_account` | Lowercase, too long | `HP_SNF_ACCT` |
| `HP-SNF-ACCT` | Wrong separator | `HP_SNF_ACCT` |

## Cross-Reference Table

For documentation, maintain a cross-reference showing the full meaning:

| Variable | Service | Description |
|----------|---------|-------------|
| `HP_SNF_ACCT` | Snowflake | Account locator (e.g., xy12345.us-east-1) |
| `HP_SNF_USER` | Snowflake | Service account username |
| `HP_SNF_PASS` | Snowflake | Service account password |
| `HP_SNF_ROLE` | Snowflake | Default role to assume |
| `HP_SNF_WH` | Snowflake | Compute warehouse name |
| `HP_SNF_DB` | Snowflake | Default database |
| `HP_SNF_SCHEMA` | Snowflake | Default schema |
| `HP_AWS_PROFILE` | AWS | Named profile for CLI |
| `HP_AWS_REGION` | AWS | Default region |

## Versioning

- **Specification Version:** 1.0
- **Effective Date:** 2025-12-15
- **Maintainer:** Health Platform Team

## Related Documentation

- [Secrets Management](../security/secrets-management.md) - How secrets are stored and accessed
- [Local Development](LOCAL_DEVELOPMENT.md) - Setting up your development environment
