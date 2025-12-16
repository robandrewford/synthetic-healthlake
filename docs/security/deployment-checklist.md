# Deployment Security Checklist

Pre-deployment security review checklist and runtime monitoring recommendations for the synthetic-healthlake platform.

## Pre-Deployment Checklist

### 🔐 Secrets and Credentials

- [ ] **Secrets Manager configured**
  - [ ] Snowflake credentials stored in `health-platform/snowflake`
  - [ ] Auth secrets stored in `health-platform/auth`
  - [ ] No secrets in environment variables or code

- [ ] **GitHub Secrets configured**
  - [ ] `AWS_ROLE_ARN` set for OIDC authentication
  - [ ] Old `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` removed
  - [ ] `AWS_REGION` set correctly

- [ ] **No hardcoded credentials**
  - [ ] Run: `git secrets --scan` or `gitleaks detect`
  - [ ] Check: `grep -r "password\|secret\|key\|token" --include="*.py" --include="*.ts"`

### 🌐 Network Security

- [ ] **S3 bucket security**
  - [ ] `blockPublicAccess: BLOCK_ALL` enabled
  - [ ] `enforceSSL: true` enabled
  - [ ] Bucket versioning enabled
  - [ ] CORS configured for trusted origins only (not `*` in production)

- [ ] **API Gateway security**
  - [ ] Lambda authorizer configured
  - [ ] CORS restricted to trusted domains
  - [ ] Rate limiting configured (if needed)

- [ ] **Lambda security**
  - [ ] Functions use ARM64 architecture (cost/security)
  - [ ] Appropriate timeout configured
  - [ ] Memory sized appropriately
  - [ ] No public URLs exposed

### 🔑 IAM and Access Control

- [ ] **IAM roles follow least privilege**
  - [ ] Review: `cdk/lib/constructs/secrets-construct.ts` permissions
  - [ ] Review: Lambda execution roles
  - [ ] No `*` actions or resources unless required

- [ ] **GitHub Actions OIDC**
  - [ ] IAM role deployed via CloudFormation
  - [ ] Trust policy restricts to specific repository
  - [ ] Session duration is minimal (1 hour)

### 🏷️ Resource Tagging

- [ ] **Tags applied to all resources**
  - [ ] `Project: fhir-omop-reference`
  - [ ] `Environment: dev/staging/prod`
  - [ ] `ManagedBy: CDK`
  - [ ] `Application: health-platform`
  - [ ] `CostCenter` set for cost tracking

### 📦 Dependencies

- [ ] **Dependency scanning clean**
  - [ ] Run: `pip-audit` (no HIGH/CRITICAL vulnerabilities)
  - [ ] Run: `cd cdk && npm audit --audit-level=high`
  - [ ] Dependabot enabled for automated updates

- [ ] **Container images scanned** (if applicable)
  - [ ] ECR image scanning enabled
  - [ ] Base images from trusted sources
  - [ ] Images updated with latest security patches

### 🔒 Data Protection

- [ ] **Encryption at rest**
  - [ ] S3 bucket encryption enabled (S3_MANAGED or KMS)
  - [ ] Secrets Manager encryption (automatic)
  - [ ] SQS encryption enabled

- [ ] **Encryption in transit**
  - [ ] HTTPS enforced on S3 bucket
  - [ ] API Gateway uses HTTPS only
  - [ ] Internal AWS communication encrypted

### ✅ Code Quality

- [ ] **Pre-commit hooks pass**
  - [ ] Run: `pre-commit run --all-files`
  - [ ] All linting checks pass
  - [ ] No security warnings

- [ ] **CDK synthesizes cleanly**
  - [ ] Run: `cd cdk && npm run build && npx cdk synth`
  - [ ] No warnings or errors

---

## Runtime Security Monitoring

### 📊 CloudWatch Metrics to Monitor

| Metric | Service | Threshold | Action |
|--------|---------|-----------|--------|
| Invocations | Lambda | Baseline deviation | Investigate spike |
| Errors | Lambda | > 0 | Alert and investigate |
| Duration | Lambda | > 80% timeout | Optimize or increase timeout |
| Throttles | Lambda | > 0 | Increase concurrency |
| 4XX Errors | API Gateway | Baseline deviation | Check client issues |
| 5XX Errors | API Gateway | > 0 | Alert and investigate |
| NumberOfMessagesReceived | SQS | Baseline deviation | Monitor queue health |
| ApproximateAgeOfOldestMessage | SQS (DLQ) | > 0 | Process failed messages |

### 🚨 Recommended CloudWatch Alarms

```bash
# Lambda errors alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "health-platform-lambda-errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions <SNS_TOPIC_ARN>

# API Gateway 5XX errors
aws cloudwatch put-metric-alarm \
  --alarm-name "health-platform-api-5xx" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions <SNS_TOPIC_ARN>
```

### 📝 Log Monitoring

**Key log patterns to monitor:**

| Pattern | Log Group | Meaning |
|---------|-----------|---------|
| `ERROR` | Lambda functions | Application errors |
| `Task timed out` | Lambda functions | Timeout issues |
| `AccessDenied` | Lambda functions | IAM permission issues |
| `UNAUTHORIZED` | API Gateway | Auth failures |
| `ThrottlingException` | Any | Service limits hit |

**CloudWatch Insights query for errors:**

```sql
fields @timestamp, @message
| filter @message like /ERROR|Exception|Failed/
| sort @timestamp desc
| limit 100
```

### 🔍 Security Event Monitoring

**AWS CloudTrail events to watch:**

| Event | Description | Action |
|-------|-------------|--------|
| `ConsoleLogin` | Console access | Verify legitimate user |
| `CreateAccessKey` | New IAM key | Review necessity |
| `PutBucketPolicy` | S3 policy change | Verify no public access |
| `CreateRole` | New IAM role | Review permissions |
| `AttachRolePolicy` | Policy attached | Verify least privilege |
| `DeleteBucket` | Bucket deleted | Verify intentional |

**CloudTrail Insights query:**

```sql
fields eventTime, eventName, userIdentity.userName, errorCode
| filter eventSource = 's3.amazonaws.com' or eventSource = 'iam.amazonaws.com'
| filter errorCode like /Denied|Unauthorized/
| sort eventTime desc
| limit 50
```

### 🛡️ Automated Security Checks

**Weekly automated checks:**

```bash
#!/bin/bash
# security-audit.sh

echo "=== Dependency Audit ==="
pip-audit
cd cdk && npm audit --audit-level=moderate

echo "=== Secret Scanning ==="
gitleaks detect --source .

echo "=== IAM Policy Analysis ==="
aws iam get-account-authorization-details > iam-report.json

echo "=== S3 Bucket Analysis ==="
aws s3api get-bucket-encryption --bucket <BUCKET_NAME>
aws s3api get-bucket-policy-status --bucket <BUCKET_NAME>

echo "=== Lambda Function Analysis ==="
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,Timeout]'
```

### 📈 Cost Monitoring

Monitor these for unexpected changes (possible security issue):

- Lambda invocations spike
- S3 data transfer increase
- API Gateway request spike
- CloudWatch Logs ingestion increase

---

## Incident Response Quick Reference

### 🚨 Suspected Security Incident

1. **Isolate**: Disable compromised credentials/resources
2. **Assess**: Review CloudTrail logs
3. **Contain**: Revoke permissions if needed
4. **Document**: Record timeline and actions
5. **Recover**: Restore from known-good state
6. **Review**: Post-incident analysis

### 🔑 Credential Compromise Response

```bash
# Immediately rotate compromised credentials
aws secretsmanager rotate-secret --secret-id health-platform/snowflake

# Disable any IAM access keys
aws iam update-access-key --user-name <USER> --access-key-id <KEY_ID> --status Inactive

# Review CloudTrail for unauthorized actions
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=<USER>
```

### 🗑️ Data Breach Response

1. Identify affected data scope
2. Notify security team immediately
3. Preserve logs and evidence
4. Follow organizational breach notification procedures
5. Document all actions taken

---

## Compliance Notes

This checklist is designed for a synthetic data platform. For real patient data:

- [ ] HIPAA BAA signed with AWS
- [ ] Additional audit logging required
- [ ] Data retention policies documented
- [ ] Access review procedures in place
- [ ] Security training completed for all operators

---

## Related Documentation

- [Security Checklist](security-checklist.md) - Detailed security features
- [Secrets Management](secrets-management.md) - Credentials handling
- [Dependency Scanning](dependency-scanning.md) - Automated vulnerability detection
- [OIDC Setup](../../.github/OIDC_SETUP.md) - GitHub Actions authentication
