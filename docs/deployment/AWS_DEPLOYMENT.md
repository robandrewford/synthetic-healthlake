# AWS Deployment Guide

This guide walks you through deploying the synthetic-healthlake stack to AWS using CDK.

## Prerequisites

### AWS Account Setup
- Active AWS account
- AWS CLI v2 installed and configured
- Appropriate IAM permissions (see below)

### Local Tools
- Node.js 20+
- AWS CDK CLI: `npm install -g aws-cdk`
- Python 3.11+
- Docker (for building container images)

## Required IAM Permissions

The deploying user/role needs permissions for:
- **CloudFormation**: Full access for stack management
- **S3**: Create buckets, put objects
- **Glue**: Create databases, tables
- **Athena**: Query execution
- **ECS**: Create clusters, task definitions, services
- **Step Functions**: Create state machines
- **VPC**: Create VPCs, subnets, security groups, endpoints
- **KMS**: Create keys, encrypt/decrypt
- **IAM**: Create roles and policies
- **CloudWatch**: Create log groups, alarms
- **ECR**: Create repositories, push images

**Recommended**: Use `AdministratorAccess` for initial deployment, then restrict.

## Deployment Steps

### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter your default region (e.g., us-west-2)
# Enter your default output format (json)
```

Verify:
```bash
aws sts get-caller-identity
```

### 2. Bootstrap CDK (First Time Only)

```bash
cd cdk
npx cdk bootstrap aws://ACCOUNT-ID/REGION
```

Replace `ACCOUNT-ID` and `REGION` with your values.

### 3. Build Container Images

```bash
# Build synthetic generator image
docker build -f docker/synthetic-generator/Dockerfile -t synthetic-generator:latest .

# Build dbt runner image
docker build -f docker/dbt-runner/Dockerfile -t dbt-runner:latest .

# Create ECR repositories (if not exists)
aws ecr create-repository --repository-name synthetic-generator || true
aws ecr create-repository --repository-name dbt-runner || true

# Get ECR login
aws ecr get-login-password --region REGION | docker login --username AWS --password-stdin ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com

# Tag and push images
docker tag synthetic-generator:latest ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/synthetic-generator:latest
docker push ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/synthetic-generator:latest

docker tag dbt-runner:latest ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/dbt-runner:latest
docker push ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/dbt-runner:latest
```

### 4. Update CDK Context

Edit `cdk/cdk.json` to reference your images:

```json
{
  "context": {
    "syntheticGeneratorImage": "ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/synthetic-generator:latest",
    "dbtRunnerImage": "ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/dbt-runner:latest"
  }
}
```

### 5. Deploy Infrastructure

```bash
cd cdk

# Install dependencies
npm install

# Compile TypeScript
npx tsc

# Preview changes
npx cdk diff

# Deploy
npx cdk deploy
```

**Note**: Deployment takes ~10-15 minutes.

### 6. Capture Outputs

After deployment, note the outputs:
```
Outputs:
FhirOmopStack.StateMachineArn = arn:aws:states:REGION:ACCOUNT:stateMachine:FhirOmopPipeline
FhirOmopStack.DataBucketName = fhiromopstack-databucket-XXXXX
FhirOmopStack.GlueDatabaseName = fhir_omop
```

## Running the Pipeline

### Trigger Step Functions Execution

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:FhirOmopPipeline \
  --name "manual-run-$(date +%Y%m%d-%H%M%S)"
```

### Monitor Execution

```bash
# List executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:FhirOmopPipeline

# Get execution details
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

Or use the AWS Console:
1. Navigate to Step Functions
2. Click on `FhirOmopPipeline`
3. View execution history

### View Logs

```bash
# ECS task logs
aws logs tail /ecs/synthetic-generator --follow

# dbt logs
aws logs tail /ecs/dbt-runner --follow
```

## Querying Results

### Using Athena Console

1. Open AWS Athena console
2. Select database: `fhir_omop`
3. Run queries:

```sql
-- View patients
SELECT * FROM dim_patient LIMIT 10;

-- View chronic conditions
SELECT * FROM fact_chronic_condition LIMIT 10;

-- Count by condition
SELECT
  chronic_condition_name,
  COUNT(*) as patient_count
FROM fact_chronic_condition
GROUP BY chronic_condition_name;
```

### Using AWS CLI

```bash
# Start query
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT * FROM fhir_omop.dim_patient LIMIT 10" \
  --result-configuration "OutputLocation=s3://YOUR-BUCKET/athena-results/" \
  --query-execution-context "Database=fhir_omop" \
  --query 'QueryExecutionId' \
  --output text)

# Get results
aws athena get-query-results --query-execution-id $QUERY_ID
```

## Updating the Stack

### Update Code

```bash
# Make changes to CDK code
cd cdk/lib

# Rebuild
npx tsc

# Preview changes
npx cdk diff

# Deploy updates
npx cdk deploy
```

### Update Container Images

```bash
# Rebuild images
docker build -f docker/synthetic-generator/Dockerfile -t synthetic-generator:latest .

# Push to ECR
docker tag synthetic-generator:latest ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/synthetic-generator:latest
docker push ACCOUNT-ID.dkr.ecr.REGION.amazonaws.com/synthetic-generator:latest

# Update ECS task definition (automatic on next execution)
```

## Cost Optimization

### Estimated Costs

For 100 patients/day:
- **S3**: ~$1/month
- **Glue Catalog**: Free tier
- **Athena**: ~$5/month (query dependent)
- **ECS Fargate**: ~$10/month (execution dependent)
- **Step Functions**: ~$1/month
- **VPC Endpoints**: ~$15/month
- **KMS**: ~$1/month

**Total**: ~$33/month

### Reduce Costs

1. **Delete VPC Endpoints** if not needed for security
2. **Use Spot instances** for ECS (not currently configured)
3. **Reduce data retention** in S3
4. **Delete old Athena results**

## Cleanup

### Delete Stack

```bash
cd cdk
npx cdk destroy
```

**Warning**: This deletes all resources including data!

### Manual Cleanup

Some resources may need manual deletion:
- S3 buckets (if not empty)
- CloudWatch log groups
- ECR repositories

## Troubleshooting

### Deployment Fails

**Error**: `Resource limit exceeded`
- **Solution**: Request limit increase in AWS Console

**Error**: `Insufficient permissions`
- **Solution**: Verify IAM permissions (see above)

### Pipeline Fails

**Error**: `Task failed to start`
- **Solution**: Check ECS task logs, verify container images exist

**Error**: `Access denied to S3`
- **Solution**: Verify IAM task role has S3 permissions

### Athena Queries Fail

**Error**: `Table not found`
- **Solution**: Verify Glue database and tables exist

**Error**: `Access denied`
- **Solution**: Verify Athena query result location permissions

## Next Steps

- **Monitor Costs**: Set up AWS Cost Explorer alerts
- **Add Dashboards**: Create CloudWatch dashboards
- **Set Up Alerts**: Configure SNS notifications for failures
- **Automate Deployments**: Set up CI/CD with GitHub Actions
