# GitHub Actions OIDC Setup Guide

This guide walks through replacing long-lived AWS credentials with OpenID Connect (OIDC) authentication for GitHub Actions.

## Why OIDC?

**Security Benefits:**
- ✅ No long-lived credentials stored in GitHub Secrets
- ✅ Automatic credential rotation
- ✅ Time-limited session tokens (1 hour)
- ✅ Fine-grained IAM permissions
- ✅ Audit trail through CloudTrail
- ✅ Repository-specific access control

**Before (Insecure):**
```yaml
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**After (Secure):**
```yaml
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
      aws-region: us-east-1
```

---

## Prerequisites

- AWS account with IAM permissions to create:
  - OIDC Identity Providers
  - IAM Roles and Policies
  - CloudFormation Stacks
- AWS CLI configured locally
- Repository admin access (to update GitHub Secrets)

---

## Step 1: Deploy the OIDC IAM Role

### Option A: Using CloudFormation (Recommended)

The CloudFormation template creates:
- GitHub OIDC Identity Provider (if not exists)
- IAM Role with trust policy for your repository
- Necessary permissions for GitHub Actions

**Deploy the stack:**

```bash
aws cloudformation create-stack \
  --stack-name github-actions-oidc-role \
  --template-body file://.github/oidc-role.yml \
  --parameters \
    ParameterKey=GitHubOrg,ParameterValue=robandrewford \
    ParameterKey=GitHubRepo,ParameterValue=synthetic-healthlake \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name github-actions-oidc-role \
  --region us-east-1

# Get the Role ARN
aws cloudformation describe-stacks \
  --stack-name github-actions-oidc-role \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
  --output text
```

**Save the Role ARN** - you'll need it in Step 2.

Example ARN:
```
arn:aws:iam::123456789012:role/synthetic-healthlake-github-actions-role
```

### Option B: Manual Setup (If OIDC Provider Already Exists)

If you already have a GitHub OIDC provider in your account:

```bash
# Find existing OIDC provider ARN
aws iam list-open-id-connect-providers

# Deploy with existing provider
aws cloudformation create-stack \
  --stack-name github-actions-oidc-role \
  --template-body file://.github/oidc-role.yml \
  --parameters \
    ParameterKey=GitHubOrg,ParameterValue=robandrewford \
    ParameterKey=GitHubRepo,ParameterValue=synthetic-healthlake \
    ParameterKey=OIDCProviderArn,ParameterValue=arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## Step 2: Update GitHub Secrets

### Add New Secret

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add:
   - **Name**: `AWS_ROLE_ARN`
   - **Value**: The Role ARN from Step 1

### Keep Existing Secrets

**Keep these secrets** (used by dbt profile configuration):
- `ATHENA_S3_STAGING_DIR`
- `AWS_REGION`

### Remove Old Secrets (After Testing)

Once OIDC is working, **delete these secrets**:
- ❌ `AWS_ACCESS_KEY_ID`
- ❌ `AWS_SECRET_ACCESS_KEY`
- ❌ `AWS_SESSION_TOKEN` (if exists)

---

## Step 3: Verify Workflows Updated

The following workflows have been updated to use OIDC:

### ✅ dbt-tests.yml (UPDATED)

```yaml
jobs:
  dbt-tests:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
```

### ℹ️ cdk-deploy.yml (No AWS Access Needed)

This workflow only runs `cdk synth` without deploying, so no AWS credentials required.

### ℹ️ synthetic-smoke.yml (No AWS Access Needed)

This workflow only compiles Python code, no AWS access required.

---

## Step 4: Test the Setup

### Test Workflow Manually

1. Go to **Actions** tab in GitHub
2. Select **dbt Tests** workflow
3. Click **Run workflow** → **Run workflow**
4. Monitor the run - look for:
   - ✅ "Configure AWS Credentials (OIDC)" step succeeds
   - ✅ dbt commands execute successfully
   - ✅ No authentication errors

### Expected Output

```
Configure AWS Credentials (OIDC)
✓ Configured AWS credentials
✓ Role ARN: arn:aws:iam::123456789012:role/synthetic-healthlake-github-actions-role
✓ Session Name: GitHubActions-dbt-tests
✓ Region: us-east-1
```

### Troubleshooting

**Error: "Not authorized to perform sts:AssumeRoleWithWebIdentity"**

→ Check the IAM Role trust policy allows your repository:
```bash
aws iam get-role --role-name synthetic-healthlake-github-actions-role \
  --query 'Role.AssumeRolePolicyDocument'
```

Should contain:
```json
{
  "Condition": {
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:robandrewford/synthetic-healthlake:*"
    }
  }
}
```

**Error: "User is not authorized to perform: athena:StartQueryExecution"**

→ The IAM Role needs additional permissions. Update the CloudFormation stack with broader permissions.

**Error: "secrets.AWS_ROLE_ARN not found"**

→ Ensure you created the `AWS_ROLE_ARN` secret in GitHub (Step 2).

---

## Step 5: Clean Up Old Credentials

After confirming OIDC works:

### Delete GitHub Secrets

```bash
# Via GitHub CLI (if installed)
gh secret delete AWS_ACCESS_KEY_ID --repo robandrewford/synthetic-healthlake
gh secret delete AWS_SECRET_ACCESS_KEY --repo robandrewford/synthetic-healthlake
```

Or manually through GitHub UI:
1. Settings → Secrets and variables → Actions
2. Delete `AWS_ACCESS_KEY_ID`
3. Delete `AWS_SECRET_ACCESS_KEY`

### Deactivate AWS IAM User (If Applicable)

If you created an IAM user specifically for GitHub Actions:

```bash
# List access keys
aws iam list-access-keys --user-name github-actions-user

# Deactivate keys
aws iam update-access-key \
  --user-name github-actions-user \
  --access-key-id AKIA... \
  --status Inactive

# After 30 days with no issues, delete:
aws iam delete-access-key \
  --user-name github-actions-user \
  --access-key-id AKIA...
```

---

## Advanced Configuration

### Adjust Role Permissions

Edit `.github/oidc-role.yml` and update the stack:

```bash
aws cloudformation update-stack \
  --stack-name github-actions-oidc-role \
  --template-body file://.github/oidc-role.yml \
  --parameters \
    ParameterKey=GitHubOrg,ParameterValue=robandrewford \
    ParameterKey=GitHubRepo,ParameterValue=synthetic-healthlake \
  --capabilities CAPABILITY_NAMED_IAM
```

### Branch-Specific Access

Restrict to specific branches by updating the trust policy condition:

```yaml
Condition:
  StringLike:
    'token.actions.githubusercontent.com:sub':
      - 'repo:robandrewford/synthetic-healthlake:ref:refs/heads/main'
      - 'repo:robandrewford/synthetic-healthlake:ref:refs/heads/develop'
```

### Multiple Repositories

Deploy separate stacks for each repository:

```bash
aws cloudformation create-stack \
  --stack-name github-actions-oidc-role-repo2 \
  --template-body file://.github/oidc-role.yml \
  --parameters \
    ParameterKey=GitHubRepo,ParameterValue=another-repo \
    ParameterKey=OIDCProviderArn,ParameterValue=arn:aws:iam::ACCOUNT:oidc-provider/token.actions.githubusercontent.com \
  --capabilities CAPABILITY_NAMED_IAM
```

---

## Security Best Practices

### ✅ Do

- Use the most restrictive IAM permissions possible
- Set `MaxSessionDuration` to minimum needed (default: 1 hour)
- Monitor CloudTrail logs for assumed role activity
- Regularly audit IAM Role permissions
- Use branch restrictions in trust policy for production
- Enable AWS Config to monitor IAM changes

### ❌ Don't

- Grant `AdministratorAccess` policy to GitHub Actions role
- Use wildcards (`*`) in resource ARNs unless necessary
- Share the same role across multiple unrelated repositories
- Disable CloudTrail logging
- Store backup credentials in GitHub Secrets "just in case"

### Monitoring

Set up CloudWatch alarms for suspicious activity:

```bash
# Monitor failed assume role attempts
aws cloudwatch put-metric-alarm \
  --alarm-name github-actions-failed-assume-role \
  --metric-name FailedAssumeRoleAttempts \
  --namespace AWS/IAM \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

## Rollback Plan

If you need to rollback to long-lived credentials:

1. **Re-create IAM User access keys** (if deleted)
2. **Add secrets back to GitHub**:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
3. **Revert workflow changes**:
   ```bash
   git revert <commit-hash>
   git push
   ```
4. **Workflows will use old authentication method**

---

## References

- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS IAM OIDC Identity Providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [aws-actions/configure-aws-credentials](https://github.com/aws-actions/configure-aws-credentials)
- [CloudFormation IAM Role Reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-role.html)

---

## Summary Checklist

- [ ] Deploy CloudFormation stack with OIDC role
- [ ] Copy Role ARN from stack outputs
- [ ] Add `AWS_ROLE_ARN` to GitHub Secrets
- [ ] Keep `ATHENA_S3_STAGING_DIR` and `AWS_REGION` secrets
- [ ] Test workflow manually in GitHub Actions
- [ ] Verify "Configure AWS Credentials (OIDC)" step succeeds
- [ ] Verify dbt commands work with OIDC credentials
- [ ] Delete old `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets
- [ ] Deactivate/delete old IAM User (if applicable)
- [ ] Document Role ARN for team members
- [ ] Set up CloudWatch monitoring (optional)
- [ ] Review IAM permissions quarterly

**Status: Ready to deploy! 🚀**
