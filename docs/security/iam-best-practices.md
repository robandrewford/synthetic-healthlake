# IAM Best Practices

This document outlines IAM (Identity and Access Management) best practices for Synthetic HealthLake, including least-privilege patterns, role definitions, and audit procedures.

## Core Principles

### Least Privilege Access

Every identity should have only the minimum permissions necessary to perform its function:

- Grant specific actions, not wildcards (`s3:GetObject` not `s3:*`)
- Scope to specific resources, not all resources (`arn:aws:s3:::bucket/*` not `*`)
- Use conditions to further restrict access
- Regularly review and remove unused permissions

### Role-Based Access Control (RBAC)

Organize permissions by function rather than individual user:

```text
┌─────────────────────────────────────────────────────────────────┐
│                    IAM Role Hierarchy                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ Service Roles   │     │ Human Roles     │                   │
│  │                 │     │                 │                   │
│  │ - ECS Task      │     │ - Admin         │                   │
│  │ - Lambda Exec   │     │ - Developer     │                   │
│  │ - Step Functions│     │ - ReadOnly      │                   │
│  │ - CI/CD         │     │ - Auditor       │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Service Roles

### ECS Task Role

Purpose: Permissions for Synthea data generation containers.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3WriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::${BucketName}/fhir/*",
        "arn:aws:s3:::${BucketName}/omop/*"
      ]
    },
    {
      "Sid": "S3ListAccess",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::${BucketName}",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "fhir/*",
            "omop/*"
          ]
        }
      }
    },
    {
      "Sid": "SecretsAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${Region}:${Account}:secret:healthlake/*"
    },
    {
      "Sid": "LogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${Region}:${Account}:log-group:/ecs/synthea-generator:*"
    }
  ]
}
```

### Lambda Execution Role

Purpose: Permissions for FHIR API Lambda functions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::${BucketName}/fhir/*"
    },
    {
      "Sid": "S3ListAccess",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::${BucketName}",
      "Condition": {
        "StringLike": {
          "s3:prefix": "fhir/*"
        }
      }
    },
    {
      "Sid": "SecretsAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${Region}:${Account}:secret:healthlake/api/*"
    },
    {
      "Sid": "VPCAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:Vpc": "arn:aws:ec2:${Region}:${Account}:vpc/${VpcId}"
        }
      }
    },
    {
      "Sid": "LogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${Region}:${Account}:log-group:/aws/lambda/fhir-*:*"
    }
  ]
}
```

### Step Functions Role

Purpose: Permissions for orchestrating the data pipeline.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECSTaskManagement",
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:StopTask",
        "ecs:DescribeTasks"
      ],
      "Resource": "*",
      "Condition": {
        "ArnEquals": {
          "ecs:cluster": "arn:aws:ecs:${Region}:${Account}:cluster/${ClusterName}"
        }
      }
    },
    {
      "Sid": "PassRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::${Account}:role/EcsTaskRole",
        "arn:aws:iam::${Account}:role/EcsExecutionRole"
      ]
    },
    {
      "Sid": "EventsIntegration",
      "Effect": "Allow",
      "Action": [
        "events:PutTargets",
        "events:PutRule",
        "events:DescribeRule"
      ],
      "Resource": "arn:aws:events:${Region}:${Account}:rule/StepFunctionsGetEventsFor*"
    }
  ]
}
```

## CDK Implementation

### Trust Policies

```typescript
// ECS Task Role with trust policy
const ecsTaskRole = new iam.Role(this, 'EcsTaskRole', {
  assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
  description: 'Role for Synthea data generation ECS tasks',
});

// Lambda Execution Role
const lambdaRole = new iam.Role(this, 'LambdaRole', {
  assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
  description: 'Role for FHIR API Lambda functions',
  managedPolicies: [
    iam.ManagedPolicy.fromAwsManagedPolicyName(
      'service-role/AWSLambdaVPCAccessExecutionRole'
    ),
  ],
});
```

### Scoped Permissions

```typescript
// S3 bucket with scoped permissions
dataBucket.grantRead(lambdaRole, 'fhir/*');
dataBucket.grantWrite(ecsTaskRole, 'fhir/*');
dataBucket.grantWrite(ecsTaskRole, 'omop/*');

// Secrets with scoped access
secret.grantRead(ecsTaskRole);
apiSecret.grantRead(lambdaRole);
```

### Permission Boundaries

```typescript
// Create permission boundary
const permissionBoundary = new iam.ManagedPolicy(this, 'PermissionBoundary', {
  statements: [
    new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:*', 'logs:*', 'secretsmanager:GetSecretValue'],
      resources: ['*'],
    }),
    new iam.PolicyStatement({
      effect: iam.Effect.DENY,
      actions: ['iam:*', 'organizations:*'],
      resources: ['*'],
    }),
  ],
});

// Apply to roles
ecsTaskRole.addPermissionBoundary(permissionBoundary);
lambdaRole.addPermissionBoundary(permissionBoundary);
```

## Human Access Roles

### Admin Role

For infrastructure management (use sparingly):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AdminAccess",
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

### Developer Role

For development and debugging:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOnlyInfra",
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "ecs:List*",
        "lambda:Get*",
        "lambda:List*",
        "s3:Get*",
        "s3:List*",
        "logs:Get*",
        "logs:Describe*",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaInvoke",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:${Region}:${Account}:function:fhir-*"
    },
    {
      "Sid": "StepFunctionsExecution",
      "Effect": "Allow",
      "Action": [
        "states:StartExecution",
        "states:StopExecution",
        "states:DescribeExecution"
      ],
      "Resource": "arn:aws:states:${Region}:${Account}:stateMachine:*"
    }
  ]
}
```

### Auditor Role

For compliance and security review:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecurityAudit",
      "Effect": "Allow",
      "Action": [
        "iam:Get*",
        "iam:List*",
        "iam:GenerateCredentialReport",
        "iam:GenerateServiceLastAccessedDetails",
        "cloudtrail:Describe*",
        "cloudtrail:Get*",
        "cloudtrail:LookupEvents",
        "config:Describe*",
        "config:Get*"
      ],
      "Resource": "*"
    }
  ]
}
```

## IAM Audit Procedures

### Regular Audits

Perform these audits on a scheduled basis:

| Audit | Frequency | Tool |
|-------|-----------|------|
| Credential report | Weekly | IAM Credential Report |
| Unused permissions | Monthly | IAM Access Analyzer |
| Policy review | Quarterly | IAM Policy Simulator |
| Access key rotation | 90 days | AWS Config Rule |

### Audit Commands

Generate credential report:

```bash
# Generate credential report
aws iam generate-credential-report

# Get credential report
aws iam get-credential-report --query 'Content' --output text | base64 -d
```

Check for unused permissions:

```bash
# List unused services
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::${ACCOUNT}:role/EcsTaskRole

# Get the results
aws iam get-service-last-accessed-details \
  --job-id <job-id>
```

Review attached policies:

```bash
# List role policies
aws iam list-attached-role-policies --role-name EcsTaskRole
aws iam list-role-policies --role-name EcsTaskRole

# Get policy details
aws iam get-role-policy --role-name EcsTaskRole --policy-name InlinePolicy
```

### AWS Config Rules

Enable these Config rules for continuous monitoring:

```typescript
// CDK Config Rules
new config.ManagedRule(this, 'IamRootAccessKey', {
  identifier: config.ManagedRuleIdentifiers.IAM_ROOT_ACCESS_KEY_CHECK,
});

new config.ManagedRule(this, 'IamUserMfa', {
  identifier: config.ManagedRuleIdentifiers.IAM_USER_MFA_ENABLED,
});

new config.ManagedRule(this, 'IamPolicyNoAdmin', {
  identifier: config.ManagedRuleIdentifiers.IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS,
});

new config.ManagedRule(this, 'IamAccessKeyRotation', {
  identifier: config.ManagedRuleIdentifiers.ACCESS_KEYS_ROTATED,
  inputParameters: {
    maxAccessKeyAge: 90,
  },
});
```

## Security Best Practices Checklist

### Identity Management

- [ ] Enable MFA for all human users
- [ ] Use IAM Identity Center for human access
- [ ] Implement password policy requirements
- [ ] Disable root account access keys

### Role Configuration

- [ ] Use roles instead of long-term credentials
- [ ] Apply permission boundaries to all roles
- [ ] Use conditions to restrict access scope
- [ ] Implement session tags for ABAC

### Policy Design

- [ ] Never use wildcard resources (`*`) in production
- [ ] Avoid wildcard actions where possible
- [ ] Use policy conditions for additional security
- [ ] Document policy purpose in descriptions

### Monitoring

- [ ] Enable CloudTrail for all regions
- [ ] Configure IAM Access Analyzer
- [ ] Set up alerts for privileged actions
- [ ] Review access patterns regularly

## Common Anti-Patterns to Avoid

### Overly Permissive Policies

```json
// ❌ BAD: Too permissive
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}

// ✅ GOOD: Scoped and specific
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::specific-bucket/specific-prefix/*"
}
```

### Missing Conditions

```json
// ❌ BAD: No conditions
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "*"
}

// ✅ GOOD: With conditions
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:123456789:secret:healthlake/*",
  "Condition": {
    "StringEquals": {
      "secretsmanager:ResourceTag/Environment": "production"
    }
  }
}
```

### Long-Term Credentials

```bash
# ❌ BAD: Using access keys in code
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...

# ✅ GOOD: Using IAM roles and instance profiles
# No credentials in code - rely on instance metadata
```

## Related Documentation

- [Network Security](network-security.md)
- [Secrets Management](secrets-management.md)
- [Security Checklist](security-checklist.md)
- [AWS Deployment Guide](../deployment/AWS_DEPLOYMENT.md)
