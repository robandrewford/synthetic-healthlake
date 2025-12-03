# Security Policy

## 1. Supported Versions
This project is in early-stage development. All versions on the `main` branch are considered supported.

## 2. Reporting a Vulnerability
To report a security issue:
1. Open a private security advisory on GitHub, or  
2. Email the maintainer directly.

Please include:
- Steps to reproduce
- Impact assessment
- Suggested remediation (optional)

## 3. Security Requirements
- All AWS resources must use encryption at rest (KMS or S3-managed).
- Use IAM least-privilege for ECS tasks, Glue, Athena, dbt runners.
- VPC interface endpoints must be enabled for:
  - S3
  - Glue
  - Athena
  - CloudWatch Logs
- No PHI, PII, or real patient data allowed. Only synthetic datasets may be used.

## 4. Dependencies
- Use `npm audit` for CDK dependencies.
- Use `pip-audit` for Python scripts.
