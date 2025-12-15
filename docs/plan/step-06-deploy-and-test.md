# Step 6: Deploy and Test

## Overview

Commands for deploying the Lambda pipeline to AWS and running end-to-end tests.

---

## Prerequisites

```bash
# Verify AWS CLI configured
aws sts get-caller-identity

# Verify SAM CLI installed
sam --version

# Verify S3 buckets exist
aws s3 ls s3://healthtech-fhir-source/
aws s3 ls s3://healthtech-data-lake/
```

---

## Initial Deployment

```bash
cd lambda_functions

# Build the SAM application
sam build

# Deploy (first time - guided mode)
sam deploy --guided

# Answer prompts:
# Stack Name: fhir-ingestion-dev
# AWS Region: us-east-1
# Parameter Environment: dev
# Parameter SourceBucket: healthtech-fhir-source
# Parameter LandingBucket: healthtech-data-lake
# Confirm changes before deploy: Y
# Allow SAM CLI IAM role creation: Y
# Save arguments to samconfig.toml: Y
```

---

## Subsequent Deployments

```bash
# Build and deploy using saved config
sam build && sam deploy

# Deploy to specific environment
sam deploy --config-env staging
sam deploy --config-env prod
```

---

## Verify Deployment

```bash
# List deployed resources
aws cloudformation describe-stack-resources \
  --stack-name fhir-ingestion-dev \
  --query 'StackResources[*].[ResourceType,LogicalResourceId,PhysicalResourceId]' \
  --output table

# Get Lambda function ARNs
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `fhir-`)].FunctionName' \
  --output table

# Get State Machine ARN
aws stepfunctions list-state-machines \
  --query 'stateMachines[?contains(name, `fhir-ingestion`)].stateMachineArn' \
  --output text
```

---

## Manual Test Execution

### Start State Machine Execution

```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?contains(name, `fhir-ingestion-dev`)].stateMachineArn' \
  --output text)

# Start execution
EXECUTION_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"source_prefix": "synthea/batch-001", "mode": "synthea"}' \
  --query 'executionArn' \
  --output text)

echo "Execution started: $EXECUTION_ARN"
```

### Monitor Execution

```bash
# Check execution status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query '[status, startDate, stopDate]' \
  --output table

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --query 'events[*].[timestamp, type, id]' \
  --output table

# Wait for completion (polling)
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION_ARN \
    --query 'status' \
    --output text)
  echo "Status: $STATUS"
  if [ "$STATUS" != "RUNNING" ]; then
    break
  fi
  sleep 10
done
```

### View Lambda Logs

```bash
# Tail logs for initiate export Lambda
aws logs tail /aws/lambda/fhir-initiate-export-dev --follow

# Tail logs for download resources Lambda
aws logs tail /aws/lambda/fhir-download-resources-dev --follow

# Search logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/fhir-download-resources-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

---

## Verify Output

```bash
# List files in landing zone
aws s3 ls s3://healthtech-data-lake/landing/fhir/ --recursive

# Check Patient NDJSON file
aws s3 cp s3://healthtech-data-lake/landing/fhir/Patient/$(date +%Y/%m/%d)/Patient.ndjson - | head -5

# Count records per resource type
for TYPE in Patient Encounter Observation Condition; do
  COUNT=$(aws s3 cp s3://healthtech-data-lake/landing/fhir/$TYPE/$(date +%Y/%m/%d)/$TYPE.ndjson - 2>/dev/null | wc -l)
  echo "$TYPE: $COUNT records"
done

# Verify NDJSON format (each line is valid JSON)
aws s3 cp s3://healthtech-data-lake/landing/fhir/Patient/$(date +%Y/%m/%d)/Patient.ndjson - | \
  head -1 | python -m json.tool > /dev/null && echo "Valid JSON"
```

---

## Test Individual Lambdas

### Test Initiate Export

```bash
# Invoke directly
aws lambda invoke \
  --function-name fhir-initiate-export-dev \
  --payload '{"source_prefix": "synthea/batch-001", "mode": "synthea"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json | python -m json.tool
```

### Test Poll Status

```bash
# Use output from initiate export
aws lambda invoke \
  --function-name fhir-poll-status-dev \
  --payload "$(cat response.json)" \
  --cli-binary-format raw-in-base64-out \
  poll_response.json

cat poll_response.json | python -m json.tool
```

### Test Download Resources

```bash
# Extract pollResult from poll_response
DOWNLOAD_INPUT=$(cat poll_response.json | python -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps({
    'export_id': data['export_id'],
    'output': data['output']
}))
")

aws lambda invoke \
  --function-name fhir-download-resources-dev \
  --payload "$DOWNLOAD_INPUT" \
  --cli-binary-format raw-in-base64-out \
  download_response.json

cat download_response.json | python -m json.tool
```

---

## Enable Scheduled Execution

```bash
# Enable EventBridge rule for daily execution
aws events enable-rule --name fhir-daily-ingestion-dev

# Verify rule is enabled
aws events describe-rule --name fhir-daily-ingestion-dev \
  --query '[Name, State, ScheduleExpression]' \
  --output table

# Disable when not needed
aws events disable-rule --name fhir-daily-ingestion-dev
```

---

## Cleanup

```bash
# Delete stack (removes all resources)
sam delete --stack-name fhir-ingestion-dev

# Or delete specific resources
aws stepfunctions delete-state-machine --state-machine-arn $STATE_MACHINE_ARN

# Clear landing zone (careful!)
aws s3 rm s3://healthtech-data-lake/landing/fhir/ --recursive
```

---

## Troubleshooting

### Lambda Timeout

```bash
# Check function configuration
aws lambda get-function-configuration \
  --function-name fhir-download-resources-dev \
  --query '[Timeout, MemorySize]'

# Update timeout if needed (max 900 seconds)
aws lambda update-function-configuration \
  --function-name fhir-download-resources-dev \
  --timeout 900
```

### Permission Errors

```bash
# Check Lambda execution role
ROLE_ARN=$(aws lambda get-function-configuration \
  --function-name fhir-download-resources-dev \
  --query 'Role' \
  --output text)

# List attached policies
aws iam list-attached-role-policies \
  --role-name $(basename $ROLE_ARN)

# View inline policies
aws iam list-role-policies \
  --role-name $(basename $ROLE_ARN)
```

### State Machine Errors

```bash
# Get detailed error from failed execution
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --query 'events[?type==`TaskFailed` || type==`ExecutionFailed`]'
```

---

## CloudWatch Dashboard

```bash
# View dashboard (if created via Terraform)
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=fhir-pipeline"

# Manual metric query
aws cloudwatch get-metric-statistics \
  --namespace AWS/States \
  --metric-name ExecutionsSucceeded \
  --dimensions Name=StateMachineArn,Value=$STATE_MACHINE_ARN \
  --start-time $(date -d '24 hours ago' --iso-8601=seconds) \
  --end-time $(date --iso-8601=seconds) \
  --period 3600 \
  --statistics Sum
```
