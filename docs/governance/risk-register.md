# Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|-------|------------|--------|------------|
| R1 | Synthetic data unrealistic or inconsistent | Medium | High | Improve domain constraints, distributions, and terminology mappings. |
| R2 | Iceberg tables misconfigured | Low | High | Use Glue Catalog validation, dbt schema tests, and CI workflows. |
| R3 | ECS tasks unable to access S3 due to IAM issues | Medium | Medium | Apply least-privilege IAM and test via synthetic smoke tests. |
| R4 | dbt failures due to schema drift | Medium | Medium | Add more dbt tests + preflight validation step. |
| R5 | Costs increase due to inefficient compute | Low | Medium | Use Fargate spot, right-size CPU/memory, enable task-level logging. |
| R6 | Athena queries slow or expensive | Medium | Medium | Partition Iceberg tables properly and optimize dbt models. |
| R7 | Governance gaps without Lake Formation | Low | Medium | Enable LF gradually for fine-grained access control. |
| R8 | Step Functions pipeline failures | Medium | Medium | Add retries, failure alerts, and test data flows. |

## Monitoring & Review
- Review risks quarterly.
- Add new risks during major architectural changes.
- Close risks once mitigations are validated.
