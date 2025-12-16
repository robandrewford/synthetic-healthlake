# Infrastructure Validation Guide

Comprehensive guide for deploying and validating the synthetic-healthlake infrastructure in a clean AWS account.

## Overview

This guide walks through the complete infrastructure validation process:

1. Pre-deployment verification
2. CDK deployment to a clean AWS account
3. Running the complete pipeline
4. Verifying all outputs
5. Documenting actual costs

**Estimated Time**: 2-3 hours for full validation

**Estimated Cost**: $5-15 for a complete test cycle (see Cost Tracking section)

---

## Prerequisites

### AWS Account Requirements

- [ ] Clean AWS account (or isolated environment)
- [ ] Account ID and region noted
- [ ] No conflicting resources from previous deployments

### Local Environment

- [ ] AWS CLI v2 installed and configured
- [ ] Node.js 20+ installed
- [ ] Python 3.11+ installed
- [ ] Docker installed and running
- [ ] AWS CDK CLI installed: `npm install -g aws-cdk`
- [ ] UV package manager installed

### Credentials Setup

```bash
# Configure AWS credentials
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-west-2)
# Enter your default output format (json)

# Verify identity
aws sts get-caller-identity
```

**Expected output:**

```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

---

## Phase 1: Pre-Deployment Verification

### 1.1 Code Quality Checks

```bash
# Navigate to project root
cd /Users/robertford/Repos/synthetic-healthlake

# Run pre-commit hooks
uv run pre-commit run --all-files

# Expected: All checks passed
```

### 1.2 CDK Synthesis Test

```bash
cd cdk

# Install dependencies
npm install

# Compile TypeScript
npx tsc

# Synthesize CloudFormation
npx cdk synth

# Expected: CloudFormation templates generated in cdk.out/
```

### 1.3 Docker Image Build Test

```bash
# Build synthetic generator image
docker build -f docker/synthetic-generator/Dockerfile -t synthetic-generator:test .

# Build dbt runner image
docker build -f docker/dbt-runner/Dockerfile -t dbt-runner:test .

# Expected: Both images build successfully
```

### 1.4 Dependency Audit

```bash
# Python dependencies
uv run pip-audit || echo "pip-audit not installed, skipping"

# Node.js dependencies
cd cdk && npm audit --audit-level=high
cd ..

# Expected: No high/critical vulnerabilities
```

---

## Phase 2: CDK Deployment

### 2.1 Bootstrap CDK (First Time Only)

```bash
# Get your account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Bootstrap CDK
cd cdk
npx cdk bootstrap aws://${ACCOUNT_ID}/${REGION}

# Expected: CDKToolkit stack created
```

**Verification:**

```bash
aws cloudformation describe-stacks --stack-name CDKToolkit --query 'Stacks[0].StackStatus'
# Expected: "CREATE_COMPLETE" or "UPDATE_COMPLETE"
```

### 2.2 Create ECR Repositories

```bash
# Create repositories for container images
aws ecr create-repository --repository-name synthetic-generator --image-scanning-configuration scanOnPush=true || echo "Repository exists"
aws ecr create-repository --repository-name dbt-runner --image-scanning-configuration scanOnPush=true || echo "Repository exists"

# Get ECR login token
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
```

### 2.3 Push Docker Images to ECR

```bash
# Build and tag images
docker build -f docker/synthetic-generator/Dockerfile -t synthetic-generator:latest .
docker build -f docker/dbt-runner/Dockerfile -t dbt-runner:latest .

# Tag for ECR
docker tag synthetic-generator:latest ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/synthetic-generator:latest
docker tag dbt-runner:latest ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/dbt-runner:latest

# Push to ECR
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/synthetic-generator:latest
docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/dbt-runner:latest
```

**Verification:**

```bash
aws ecr describe-images --repository-name synthetic-generator --query 'imageDetails[0].imagePushedAt'
aws ecr describe-images --repository-name dbt-runner --query 'imageDetails[0].imagePushedAt'
# Expected: Recent timestamps
```

### 2.4 Update CDK Context

Edit `cdk/cdk.json` to reference your images:

```bash
# Update cdk.json with your ECR image URIs
cat > cdk/cdk.context.json << EOF
{
  "syntheticImage": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/synthetic-generator:latest",
  "dbtImage": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/dbt-runner:latest"
}
EOF
```

### 2.5 Deploy Stacks

```bash
cd cdk

# Preview changes
npx cdk diff

# Deploy all stacks (interactive approval)
npx cdk deploy --all

# Or deploy specific stacks
# npx cdk deploy FhirOmopStack
# npx cdk deploy HealthPlatformStack
```

**Expected Duration**: 10-15 minutes

**Expected Outputs** (capture these):

```text
Outputs:
FhirOmopStack.DataBucketName = fhiromopstack-fhiromopdatabucket-XXXXX
FhirOmopStack.GlueDatabaseName = fhir_omop
FhirOmopStack.ClusterName = FhirOmopStack-FhirOmopCluster-XXXXX
FhirOmopStack.StateMachineArn = arn:aws:states:REGION:ACCOUNT:stateMachine:FhirOmopPipeline
FhirOmopStack.KmsKeyId = XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

HealthPlatformStack.HealthBucketName = healthplatformstack-healthplatformbucket-XXXXX
HealthPlatformStack.ApiEndpoint = https://XXXXXXX.execute-api.REGION.amazonaws.com
HealthPlatformStack.SnowflakeSecretArn = arn:aws:secretsmanager:REGION:ACCOUNT:secret:health-platform/snowflake-XXXXX
```

---

## Phase 3: Deployment Verification

### 3.1 Verify VPC and Network

```bash
# List VPCs
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=fhir-omop-reference" \
  --query 'Vpcs[*].[VpcId,State,CidrBlock]' --output table

# Expected: VPC in 'available' state

# Check VPC endpoints
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query 'VpcEndpoints[*].[ServiceName,State]' --output table

# Expected: S3, Glue, Athena, CloudWatch, ECR, Secrets Manager endpoints
```

### 3.2 Verify S3 Buckets

```bash
# List buckets with project tag
aws s3api list-buckets --query 'Buckets[*].Name' | grep -E "fhiromop|healthplatform"

# Verify encryption (use actual bucket name from outputs)
aws s3api get-bucket-encryption --bucket <DATA_BUCKET_NAME>

# Expected: SSEAlgorithm: aws:kms

# Verify public access block
aws s3api get-public-access-block --bucket <DATA_BUCKET_NAME>

# Expected: All Block* settings = true
```

### 3.3 Verify ECS Cluster

```bash
# Get cluster status
aws ecs describe-clusters --clusters <CLUSTER_NAME> \
  --query 'clusters[0].[clusterName,status,registeredContainerInstancesCount]'

# Expected: status = ACTIVE

# List task definitions
aws ecs list-task-definitions --family-prefix FhirOmopStack

# Expected: SyntheticTaskDef and DbtTaskDef listed
```

### 3.4 Verify Glue Database

```bash
aws glue get-database --name fhir_omop

# Expected: Database exists with correct name
```

### 3.5 Verify Secrets Manager

```bash
# List secrets
aws secretsmanager list-secrets --filters Key=tag-key,Values=Project \
  --query 'SecretList[*].[Name,Description]' --output table

# Expected: health-platform/snowflake and health-platform/auth secrets
```

### 3.6 Verify Lambda Functions

```bash
# List Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `HealthPlatform`)].FunctionName'

# Expected: Patient, Encounter, Observation, Webhook, Presigned, Authorizer functions
```

### 3.7 Verify API Gateway

```bash
# Get API endpoint
aws apigatewayv2 get-apis --query 'Items[?Name==`HealthPlatformApi`].[ApiEndpoint,ProtocolType]'

# Test health endpoint (should return 401 without auth)
curl -s -o /dev/null -w "%{http_code}" <API_ENDPOINT>/Patient

# Expected: 401 (unauthorized - auth working)
```

---

## Phase 4: Pipeline Execution

### 4.1 Configure Secrets (Required Before Pipeline)

```bash
# Set Snowflake credentials (use your actual values)
aws secretsmanager put-secret-value \
  --secret-id health-platform/snowflake \
  --secret-string '{"account":"your-account","user":"your-user","password":"your-password","warehouse":"your-warehouse","database":"HEALTH_PLATFORM_DB","schema":"RAW"}'

# Set auth secrets for JWT validation
aws secretsmanager put-secret-value \
  --secret-id health-platform/auth \
  --secret-string '{"jwt_secret":"your-jwt-secret-min-32-chars","api_keys":"key1,key2","admin_api_key":"admin-key"}'
```

### 4.2 Execute Step Functions Pipeline

```bash
# Get state machine ARN from outputs
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name FhirOmopStack \
  --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' --output text)

# Start execution
EXECUTION_NAME="validation-$(date +%Y%m%d-%H%M%S)"
aws stepfunctions start-execution \
  --state-machine-arn ${STATE_MACHINE_ARN} \
  --name ${EXECUTION_NAME} \
  --input '{"patientCount": 100}'

# Expected: executionArn returned
```

### 4.3 Monitor Pipeline Execution

```bash
# Get execution ARN
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn ${STATE_MACHINE_ARN} \
  --status-filter RUNNING \
  --query 'executions[0].executionArn' --output text)

# Monitor status (poll until complete)
watch -n 10 "aws stepfunctions describe-execution --execution-arn ${EXECUTION_ARN} --query 'status'"

# Or use Step Functions console for visual monitoring
# https://console.aws.amazon.com/states/home#/statemachines
```

**Expected Duration**: 15-30 minutes depending on patient count

### 4.4 View ECS Task Logs

```bash
# View synthetic generator logs
aws logs tail /aws/ecs/FhirOmopStack-FhirOmopTaskLogs --follow

# Expected: Logs showing data generation progress
```

---

## Phase 5: Output Verification

### 5.1 Verify S3 Data

```bash
# List generated data
DATA_BUCKET=$(aws cloudformation describe-stacks --stack-name FhirOmopStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DataBucketName`].OutputValue' --output text)

aws s3 ls s3://${DATA_BUCKET}/ --recursive --human-readable

# Expected structure:
# fhir/patients.ndjson
# omop/person.parquet
# omop/condition_occurrence.parquet
# omop/measurement.parquet
```

### 5.2 Verify Data Quality

```bash
# Download and inspect sample data
aws s3 cp s3://${DATA_BUCKET}/fhir/patients.ndjson ./validation-output/
aws s3 cp s3://${DATA_BUCKET}/omop/person.parquet ./validation-output/

# Count FHIR patients
wc -l validation-output/patients.ndjson

# Expected: ~100 lines (1 per patient)

# Inspect OMOP data (requires pyarrow)
python3 -c "
import pyarrow.parquet as pq
table = pq.read_table('validation-output/person.parquet')
print(f'OMOP Persons: {table.num_rows}')
print(f'Columns: {table.column_names}')
"
```

### 5.3 Verify Glue Tables (If Created)

```bash
# List tables in Glue database
aws glue get-tables --database-name fhir_omop --query 'TableList[*].Name'

# Expected: dim_patient, fact_chronic_condition, etc.
```

### 5.4 Verify API Functionality

```bash
# Generate a test JWT (for local testing only)
# In production, use proper authentication

# Test Patient API (requires valid JWT)
curl -H "Authorization: Bearer <JWT>" <API_ENDPOINT>/Patient | jq '.total'

# Expected: Patient count returned
```

---

## Phase 6: Cost Tracking

### 6.1 Enable Cost Allocation Tags

```bash
# Ensure cost allocation tags are enabled in AWS Billing Console
# Navigate to: AWS Billing > Cost Allocation Tags > Activate tags
# Enable: Project, Environment, Application, CostCenter
```

### 6.2 Generate Cost Report

After running the validation (wait 24-48 hours for cost data):

```bash
# Get cost for the validation period
aws ce get-cost-and-usage \
  --time-period Start=YYYY-MM-DD,End=YYYY-MM-DD \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Tags":{"Key":"Project","Values":["fhir-omop-reference"]}}' \
  --group-by Type=DIMENSION,Key=SERVICE
```

### 6.3 Cost Tracking Template

Create `docs/operations/cost-analysis-YYYYMMDD.md` with:

```markdown
# Cost Analysis - [Date]

## Validation Details

- **Date**: YYYY-MM-DD
- **Duration**: X hours
- **Patient Count**: 100
- **Region**: us-west-2

## Service Costs

| Service | Cost (USD) | Notes |
|---------|-----------|-------|
| EC2 (ECS Fargate) | $X.XX | Pipeline execution |
| S3 | $X.XX | Data storage |
| VPC Endpoints | $X.XX | Private networking |
| KMS | $X.XX | Encryption keys |
| CloudWatch | $X.XX | Logs and metrics |
| Step Functions | $X.XX | Workflow orchestration |
| Lambda | $X.XX | API functions |
| API Gateway | $X.XX | HTTP API |
| Secrets Manager | $X.XX | Credentials |
| Glue Catalog | $X.XX | Metadata |
| NAT Gateway | $X.XX | Outbound traffic |
| **Total** | **$X.XX** | |

## Monthly Projection

Based on validation data, projected monthly costs:

- **Development (low usage)**: $30-50/month
- **Production (daily pipeline)**: $100-150/month

## Cost Optimization Recommendations

1. Use Spot Fargate for non-critical workloads
2. Consider removing VPC endpoints if not required
3. Reduce NAT Gateway usage with VPC endpoints
4. Use S3 Intelligent-Tiering for data
```

---

## Phase 7: Cleanup (Optional)

### 7.1 Delete CDK Stacks

```bash
cd cdk

# Destroy all stacks
npx cdk destroy --all

# Confirm deletion when prompted
```

### 7.2 Manual Cleanup

Some resources may require manual deletion:

```bash
# Delete ECR repositories
aws ecr delete-repository --repository-name synthetic-generator --force
aws ecr delete-repository --repository-name dbt-runner --force

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /aws/ecs/FhirOmopStack-FhirOmopTaskLogs

# Delete S3 bucket contents (if not auto-deleted)
aws s3 rm s3://${DATA_BUCKET} --recursive
```

### 7.3 Verify Cleanup

```bash
# Check for remaining resources
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `FhirOmop`) || contains(StackName, `HealthPlatform`)].StackName'

# Expected: Empty list
```

---

## Validation Checklist

### Pre-Deployment

- [ ] AWS credentials configured
- [ ] CDK synthesizes without errors
- [ ] Docker images build successfully
- [ ] No critical dependency vulnerabilities

### Deployment

- [ ] CDK bootstrap successful
- [ ] ECR repositories created
- [ ] Docker images pushed
- [ ] All CDK stacks deployed
- [ ] Stack outputs captured

### Infrastructure Verification

- [ ] VPC created with proper subnets
- [ ] VPC endpoints active
- [ ] S3 buckets encrypted and secure
- [ ] ECS cluster active
- [ ] Glue database exists
- [ ] Secrets created
- [ ] Lambda functions deployed
- [ ] API Gateway accessible

### Pipeline Execution

- [ ] Secrets configured with valid credentials
- [ ] Step Functions execution started
- [ ] Pipeline completed successfully
- [ ] ECS tasks ran without errors

### Output Verification

- [ ] FHIR data in S3
- [ ] OMOP data in S3
- [ ] Data quality validated
- [ ] API returns expected results

### Documentation

- [ ] Costs tracked
- [ ] Issues documented
- [ ] Screenshots captured

---

## Troubleshooting

### Deployment Fails

**Error**: `Resource limit exceeded`

- **Solution**: Request limit increase in AWS Console for the specific service

**Error**: `Access Denied`

- **Solution**: Verify IAM permissions include all required services

### Pipeline Fails

**Error**: `Task failed to start`

- **Solution**: Check ECS task logs, verify container images exist in ECR

**Error**: `Secret not found`

- **Solution**: Ensure secrets are created and have values

### Data Not Generated

**Error**: `S3 bucket empty after pipeline`

- **Solution**: Check ECS task logs for errors, verify S3 permissions

---

## Related Documentation

- [AWS Deployment Guide](AWS_DEPLOYMENT.md)
- [Security Deployment Checklist](../security/deployment-checklist.md)
- [Cost Management Strategy](../operations/cost-management-strategy.md)
- [Observability Plan](../operations/observability-plan.md)
