# Cost Analysis Guide

This document provides a framework for tracking and analyzing AWS costs for the synthetic-healthlake platform.

## Cost Tracking Overview

### Tagged Resources

All resources are tagged with:

- **Project**: `fhir-omop-reference`
- **Environment**: `dev` / `staging` / `prod`
- **Application**: `health-platform` or `fhir-omop`
- **CostCenter**: `healthcare-analytics`

### Enabling Cost Allocation Tags

1. Navigate to AWS Billing Console
2. Go to **Cost Allocation Tags**
3. Activate the following tags:
   - `Project`
   - `Environment`
   - `Application`
   - `CostCenter`
   - `Owner`

---

## Service Cost Breakdown

### FhirOmopStack Services

| Service | Component | Pricing Model | Estimated Monthly Cost |
|---------|-----------|---------------|----------------------|
| **VPC** | NAT Gateway | $0.045/hour + $0.045/GB | $32-50 |
| **VPC Endpoints** | Interface Endpoints (6) | $0.01/hour each | $43 |
| **S3** | Data Storage | $0.023/GB/month | $1-10 |
| **KMS** | Customer Managed Key | $1/month + API calls | $1-2 |
| **ECS Fargate** | Task Execution | vCPU/memory per second | $5-30 |
| **Step Functions** | State Transitions | $0.025/1000 transitions | $1-5 |
| **CloudWatch** | Logs & Metrics | $0.50/GB ingested | $5-10 |
| **Glue Catalog** | Tables & Partitions | Free tier (first 1M) | $0 |

### HealthPlatformStack Services

| Service | Component | Pricing Model | Estimated Monthly Cost |
|---------|-----------|---------------|----------------------|
| **Lambda** | API Functions | $0.20/million requests | $0-5 |
| **API Gateway** | HTTP API | $1.00/million requests | $0-5 |
| **S3** | Data Lake Bucket | $0.023/GB/month | $1-5 |
| **SQS** | Ingestion Queue | $0.40/million requests | $0-1 |
| **Secrets Manager** | 2 Secrets | $0.40/secret/month | $0.80 |
| **CloudWatch** | Logs | $0.50/GB ingested | $2-5 |

---

## Cost Scenarios

### Development Environment

- **Usage Pattern**: Occasional testing, low volume
- **Pipeline Runs**: 2-3 per week
- **Data Volume**: < 1 GB

| Component | Monthly Cost |
|-----------|-------------|
| VPC (with endpoints) | $75 |
| ECS Fargate | $5 |
| S3 | $1 |
| Lambda/API Gateway | $1 |
| CloudWatch | $5 |
| Other | $5 |
| **Total** | **~$92/month** |

- **Cost Optimization**: Remove VPC endpoints to save ~$43/month

### Staging Environment

- **Usage Pattern**: Daily testing
- **Pipeline Runs**: Once daily
- **Data Volume**: 1-10 GB

| Component | Monthly Cost |
|-----------|-------------|
| VPC (with endpoints) | $75 |
| ECS Fargate | $20 |
| S3 | $5 |
| Lambda/API Gateway | $5 |
| CloudWatch | $10 |
| Other | $10 |
| **Total** | **~$125/month** |

### Production Environment

- **Usage Pattern**: Continuous operation
- **Pipeline Runs**: Multiple daily
- **Data Volume**: 10-100 GB

| Component | Monthly Cost |
|-----------|-------------|
| VPC (with endpoints) | $75 |
| ECS Fargate | $50 |
| S3 | $20 |
| Lambda/API Gateway | $20 |
| CloudWatch | $20 |
| Other | $15 |
| **Total** | **~$200/month** |

---

## Cost Optimization Strategies

### Immediate Savings

1. **Remove VPC Endpoints** (if not required for compliance)
   - Savings: ~$43/month
   - Trade-off: Traffic routes through internet/NAT

2. **Use S3 Intelligent-Tiering**
   - Automatically moves infrequently accessed data
   - Savings: Up to 40% on storage costs

3. **Reduce CloudWatch Log Retention**
   - Change from 1 week to 3 days for non-critical logs
   - Savings: ~50% on log costs

### Long-Term Optimization

1. **ECS Fargate Spot**
   - Use Spot capacity for non-critical tasks
   - Savings: Up to 70% on Fargate costs
   - Trade-off: Tasks may be interrupted

2. **Reserved Capacity**
   - Commit to 1-year Savings Plans
   - Savings: Up to 50% on compute costs

3. **Right-Sizing**
   - Monitor actual resource utilization
   - Reduce task CPU/memory if underutilized

---

## Cost Monitoring

### CloudWatch Alarms

Create billing alarms to monitor costs:

```bash
# Create SNS topic for billing alerts
aws sns create-topic --name billing-alerts

# Subscribe to alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create billing alarm (monthly budget: $100)
aws cloudwatch put-metric-alarm \
  --alarm-name "Monthly-Budget-Alert" \
  --alarm-description "Alert when monthly spend exceeds $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:billing-alerts \
  --dimensions Name=Currency,Value=USD
```

### AWS Cost Explorer Queries

View costs by project:

```bash
# Get daily costs for the project
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{"Tags":{"Key":"Project","Values":["fhir-omop-reference"]}}' \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Budget Setup

Create a monthly budget:

```bash
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget '{
    "BudgetName": "synthetic-healthlake-monthly",
    "BudgetLimit": {"Amount": "100", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "TagKeyValue": ["user:Project$fhir-omop-reference"]
    }
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [{
      "SubscriptionType": "EMAIL",
      "Address": "your-email@example.com"
    }]
  }]'
```

---

## Cost Analysis Template

Use this template to document actual costs after validation:

```markdown
# Cost Analysis - [YYYY-MM-DD]

## Validation Details

- **Date**: YYYY-MM-DD
- **Duration**: X hours
- **Patient Count**: XXX
- **Region**: us-west-2
- **Stack**: FhirOmopStack + HealthPlatformStack

## Actual Service Costs

| Service | Cost (USD) | Notes |
|---------|-----------|-------|
| EC2 (NAT Gateway) | $X.XX | |
| VPC Endpoints | $X.XX | |
| ECS Fargate | $X.XX | |
| S3 | $X.XX | |
| KMS | $X.XX | |
| CloudWatch | $X.XX | |
| Step Functions | $X.XX | |
| Lambda | $X.XX | |
| API Gateway | $X.XX | |
| Secrets Manager | $X.XX | |
| Glue | $X.XX | |
| **Total** | **$X.XX** | |

## Cost Per Pipeline Run

- **Average run duration**: X minutes
- **Estimated cost per run**: $X.XX
- **Projected daily cost**: $X.XX

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]
```

---

## Free Tier Considerations

Some services have free tier allowances (first 12 months):

| Service | Free Tier | Monthly Value |
|---------|-----------|---------------|
| Lambda | 1M requests, 400K GB-seconds | ~$18 |
| API Gateway | 1M HTTP API calls | ~$1 |
| S3 | 5 GB storage | ~$0.12 |
| CloudWatch | 10 custom metrics, 5 GB logs | ~$5 |
| Secrets Manager | None | - |

**Note**: Always-free tier items (beyond 12 months):

- Lambda: 1M requests/month
- CloudWatch: 10 custom metrics

---

## Cost Comparison: With vs Without VPC Endpoints

### With VPC Endpoints (Recommended for Production)

| Component | Monthly Cost |
|-----------|-------------|
| Interface Endpoints (6) | $43.20 |
| Gateway Endpoint (S3) | $0.00 |
| NAT Gateway | $32.40 |
| Data Transfer | $5.00 |
| **Total Network Cost** | **~$80** |

- **Benefits**: Private connectivity, no data exposure
- **Use case**: Production, compliance requirements

### Without VPC Endpoints (Development Only)

| Component | Monthly Cost |
|-----------|-------------|
| NAT Gateway | $32.40 |
| Data Transfer | $15.00 |
| **Total Network Cost** | **~$47** |

- **Benefits**: Lower cost
- **Trade-off**: Traffic routes through public internet (via NAT)
- **Use case**: Development, testing

---

## Related Documentation

- [Infrastructure Validation Guide](../deployment/INFRASTRUCTURE_VALIDATION.md)
- [Cost Management Strategy](cost-management-strategy.md)
- [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md)
