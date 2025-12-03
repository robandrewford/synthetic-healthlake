# Access Control Matrix

## 1. Roles
| Role | Description |
|------|-------------|
| Admin | Full access to AWS infra + deploy |
| Data Engineer | ECS/dbt/S3 modification access |
| Analyst | Read-only Athena and dbt docs |
| API Service | Scoped IAM role for API runtime |
| Synthetic Generator | Restricted S3 write-only to raw zones |

## 2. Resources & Permissions

### S3
| Resource | Admin | Data Engineer | Analyst | API | Synthetic |
|----------|--------|---------------|---------|-----|-----------|
| Raw Data | RW | RW | R | R | W |
| Iceberg Tables | RW | RW | R | R | - |

### Glue Catalog
| Resource | Admin | Data Engineer | Analyst | API |
|----------|--------|---------------|---------|-----|
| Database | RW | RW | R | R |
| Tables | RW | RW | R | R |

### ECS
| Action | Admin | Data Engineer | Analyst |
|--------|--------|---------------|---------|
| Run Tasks | Y | Y | N |
| Modify Task Defs | Y | Y | N |

### Athena
| Query | Admin | Data Engineer | Analyst |
|--------|--------|---------------|---------|
| SELECT | Y | Y | Y |
| CREATE TABLE | Y | Y | N |

## 3. Governance Notes
- Prefer least privilege
- Segment roles per ECS task type
- Plan migration to Lake Formation for column-level access
