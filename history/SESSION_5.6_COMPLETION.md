# Session 5.6: GitHub Actions OIDC Completion Summary

**Date**: December 15, 2025  
**Task**: Replace long-lived AWS credentials with OpenID Connect (OIDC) authentication  
**Beads Issue**: `synthetic-healthlake-ptl.5.6`  
**Priority**: 1 (High - Security)  
**Status**: ✅ COMPLETE

---

## Executive Summary

Successfully implemented OpenID Connect (OIDC) authentication for GitHub Actions, replacing insecure long-lived AWS credentials with short-lived, automatically rotated tokens. This significantly improves the security posture of the CI/CD pipeline.

---

## What Was Implemented

### 1. CloudFormation Template for OIDC IAM Role

**File**: `.github/oidc-role.yml`

Creates the complete OIDC infrastructure:
- GitHub OIDC Identity Provider (if not exists)
- IAM Role with repository-specific trust policy
- Fine-grained permissions for:
  - S3 data lake access
  - Athena query execution (for dbt)
  - Glue Catalog operations (for dbt)
  - CloudFormation (for CDK deployments)
  - Lambda read access

**Key Security Features**:
- ✅ Repository-specific access control
- ✅ 1-hour session duration
- ✅ Least-privilege IAM permissions
- ✅ Conditional access based on GitHub repository

**Deployment**:
```bash
aws cloudformation create-stack \
  --stack-name github-actions-oidc-role \
  --template-body file://.github/oidc-role.yml \
  --parameters ParameterKey=GitHubOrg,ParameterValue=robandrewford \
               ParameterKey=GitHubRepo,ParameterValue=synthetic-healthlake \
  --capabilities CAPABILITY_NAMED_IAM
```

### 2. Updated GitHub Actions Workflow

**File**: `.github/workflows/dbt-tests.yml`

**Before (Insecure)**:
```yaml
steps:
  - name: dbt seed/run/test
    env:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**After (Secure)**:
```yaml
jobs:
  dbt-tests:
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS Credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
          role-session-name: GitHubActions-dbt-tests
      
      - name: dbt seed/run/test
        # AWS credentials automatically available
        run: dbt run
```

**Changes**:
- Added `permissions` block for OIDC token generation
- Added OIDC authentication step
- Removed hardcoded AWS credentials from environment variables
- Credentials now automatically injected by AWS action

### 3. Comprehensive Setup Documentation

**File**: `.github/OIDC_SETUP.md` (500+ lines)

Complete step-by-step guide covering:
- **Why OIDC?** - Security benefits explanation
- **Prerequisites** - Required AWS/GitHub permissions
- **Step 1**: Deploy OIDC IAM Role (CloudFormation)
- **Step 2**: Update GitHub Secrets
- **Step 3**: Verify Workflows
- **Step 4**: Test Setup
- **Step 5**: Clean Up Old Credentials
- **Advanced Configuration**: Branch restrictions, multi-repo setup
- **Security Best Practices**: Do's and Don'ts
- **Monitoring**: CloudWatch alarms for security
- **Troubleshooting**: Common errors and solutions
- **Rollback Plan**: How to revert if needed

---

## Security Improvements

### Before vs After

| Aspect | Before (Long-lived Credentials) | After (OIDC) |
|--------|--------------------------------|--------------|
| **Credential Storage** | ❌ In GitHub Secrets (permanent) | ✅ No storage (temporary tokens) |
| **Credential Lifetime** | ❌ Never expire (until manually rotated) | ✅ 1 hour max session |
| **Rotation** | ❌ Manual, infrequent | ✅ Automatic, every run |
| **Access Scope** | ❌ Broad (all AWS services) | ✅ Fine-grained (specific resources) |
| **Repository Isolation** | ❌ Same creds across repos | ✅ Per-repository roles |
| **Compromise Risk** | ❌ High (if leaked, full access) | ✅ Low (time-limited, specific scope) |
| **Audit Trail** | ⚠️ IAM user actions | ✅ Federated identity with repo context |

### Attack Surface Reduction

**Eliminated Risks**:
- ❌ Credentials leaked in logs/artifacts
- ❌ Credentials committed to repository
- ❌ Credentials stolen from GitHub Secrets
- ❌ Lateral movement after compromise
- ❌ Long-term credential abuse

**New Protections**:
- ✅ Time-limited access (1 hour)
- ✅ Repository-scoped trust policy
- ✅ CloudTrail audit logging with GitHub context
- ✅ Automatic credential rotation
- ✅ No credential storage required

---

## Files Created/Modified

### New Files

1. **`.github/oidc-role.yml`**
   - CloudFormation template for OIDC infrastructure
   - 192 lines with comprehensive IAM policies

2. **`.github/OIDC_SETUP.md`**
   - Complete setup and troubleshooting guide
   - 500+ lines of documentation
   - Step-by-step deployment instructions

### Modified Files

1. **`.github/workflows/dbt-tests.yml`**
   - Added OIDC permissions
   - Added AWS credentials configuration step
   - Removed hardcoded credential environment variables

---

## Implementation Status

### ✅ Completed

- [x] CloudFormation template created
- [x] IAM Role with least-privilege permissions
- [x] OIDC Identity Provider configuration
- [x] Trust policy for repository-specific access
- [x] Updated dbt-tests.yml workflow
- [x] Removed credential environment variables
- [x] Comprehensive setup documentation
- [x] Troubleshooting guide
- [x] Security best practices documented
- [x] Rollback plan documented

### ⏭️ Next Steps (User Action Required)

1. **Deploy CloudFormation Stack**
   ```bash
   aws cloudformation create-stack \
     --stack-name github-actions-oidc-role \
     --template-body file://.github/oidc-role.yml \
     --parameters ParameterKey=GitHubOrg,ParameterValue=robandrewford \
                  ParameterKey=GitHubRepo,ParameterValue=synthetic-healthlake \
     --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Get Role ARN**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name github-actions-oidc-role \
     --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
     --output text
   ```

3. **Add GitHub Secret**
   - Go to GitHub Settings → Secrets and variables → Actions
   - Create `AWS_ROLE_ARN` secret with the Role ARN

4. **Test Workflow**
   - Run dbt Tests workflow manually
   - Verify OIDC authentication succeeds

5. **Clean Up Old Credentials**
   - Delete `AWS_ACCESS_KEY_ID` from GitHub Secrets
   - Delete `AWS_SECRET_ACCESS_KEY` from GitHub Secrets
   - Deactivate IAM User access keys (if applicable)

---

## Other Workflows Status

### ℹ️ cdk-deploy.yml - No Changes Needed

Currently only runs `cdk synth` which doesn't require AWS credentials.

**If deploying CDK in future**, add OIDC authentication:
```yaml
jobs:
  cdk-deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      - run: npx cdk deploy
```

### ℹ️ synthetic-smoke.yml - No Changes Needed

Only compiles Python code, no AWS access required.

---

## Security Best Practices Implemented

### ✅ Least Privilege Access

IAM Role grants only necessary permissions:
- S3: Limited to project buckets (`synthetic-healthlake-*`)
- Athena: Query execution only
- Glue: Catalog read/write for dbt
- CloudFormation: Read-only stack operations
- Lambda: Read-only function metadata

### ✅ Conditional Trust Policy

Trust policy restricts access to:
- Specific GitHub organization: `robandrewford`
- Specific repository: `synthetic-healthlake`
- Any branch/tag (can be further restricted)

### ✅ Time-Limited Sessions

- Maximum session duration: 1 hour
- Credentials automatically expire
- New tokens generated for each workflow run

### ✅ Audit Trail

CloudTrail logs show:
- Repository that assumed the role
- Workflow run ID
- Branch/tag reference
- Timestamp and duration

---

## Testing Checklist

Before deleting old credentials, verify:

- [ ] CloudFormation stack deployed successfully
- [ ] Role ARN added to GitHub Secrets
- [ ] Manual workflow run succeeds
- [ ] "Configure AWS Credentials (OIDC)" step passes
- [ ] dbt commands execute without auth errors
- [ ] CloudTrail shows AssumeRoleWithWebIdentity events
- [ ] No errors in GitHub Actions logs

---

## Rollback Procedure

If issues occur:

1. **Keep old credentials in GitHub Secrets temporarily**
2. **Test OIDC setup thoroughly**
3. **Only delete old credentials after 30 days of stable operation**
4. **If rollback needed**:
   ```bash
   git revert <commit-hash>
   git push
   ```
5. **Workflows revert to old authentication**

---

## Monitoring & Maintenance

### Recommended Monitoring

Set up CloudWatch alarms for:
- Failed AssumeRole attempts (threshold: 5 in 5 minutes)
- Unusual access patterns
- Permission denied errors

### Quarterly Review

- Review IAM Role permissions
- Check CloudTrail logs for anomalies
- Update trust policy if repository changes
- Rotate GitHub OIDC thumbprint if updated

---

## Cost Impact

**Zero additional cost**:
- OIDC is a free AWS feature
- No EC2, Lambda, or other compute charges
- Only standard CloudTrail logging costs (typically negligible)

**Improved security**:
- Reduces risk of credential compromise
- Eliminates manual rotation effort
- Provides better audit trail

---

## Compliance Benefits

### Security Frameworks

OIDC implementation helps meet requirements for:
- **SOC 2**: Credential management, least privilege
- **ISO 27001**: Access control, authentication
- **CIS AWS Foundations**: IAM best practices
- **NIST**: Identity and access management
- **PCI DSS**: Credential protection (if handling payment data)

### Audit Evidence

CloudTrail logs provide:
- Who accessed AWS (GitHub repository)
- When access occurred (timestamp)
- What actions were performed (API calls)
- From where (GitHub Actions runner)

---

## References

- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS IAM OIDC Providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
- [OWASP CI/CD Security Best Practices](https://owasp.org/www-project-devsecops-guideline/)

---

## Conclusion

Session 5.6 successfully eliminates long-lived AWS credentials from GitHub Actions, implementing industry best practice for CI/CD security. The OIDC setup provides:

- ✅ **Better Security**: Time-limited, automatically rotated credentials
- ✅ **Better Compliance**: Audit trail with GitHub context
- ✅ **Better Operations**: No manual credential rotation
- ✅ **Better Isolation**: Per-repository access control

The implementation is production-ready and includes comprehensive documentation for deployment, testing, troubleshooting, and maintenance.

**Next Action**: Deploy the CloudFormation stack and test the OIDC setup following `.github/OIDC_SETUP.md`
