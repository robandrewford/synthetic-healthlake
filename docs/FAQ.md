# Frequently Asked Questions (FAQ)

## General Questions

### What is this project?

This is a reference architecture demonstrating how to build a modern healthcare data pipeline that:
- Generates synthetic FHIR and OMOP data
- Validates data quality
- Stores data in Apache Iceberg tables
- Transforms data with dbt
- Orchestrates workflows with AWS Step Functions

It's designed for learning, prototyping, and as a starting point for production systems.

### Is this production-ready?

**Partially**. The project is ~70% complete as a reference architecture:
- ✅ Core functionality works end-to-end
- ✅ Infrastructure follows AWS best practices
- ✅ Security features (KMS, VPC endpoints, IAM)
- ⚠️ Needs additional testing for production scale
- ⚠️ Monitoring and alerting need enhancement

### Can I use real patient data?

**No**. This project is designed for **synthetic data only**. Never use real patient data without:
- Proper HIPAA compliance
- Data use agreements
- IRB approval (if applicable)
- Legal review

## Setup and Installation

### What are the minimum requirements?

**Local development:**
- Python 3.11+
- 4GB RAM
- 1GB disk space

**AWS deployment:**
- AWS account
- ~$30-50/month budget
- IAM permissions for deployment

### Do I need Docker?

**No**, Docker is optional. You can:
- Run everything with Python locally
- Use Docker for containerized testing
- Deploy to AWS without local Docker (uses ECR)

### Why use `uv` instead of `pip`?

`uv` is faster and handles dependencies better, but `pip` works fine:
```bash
# Using pip
pip install -e .
python synthetic/generators/unified_generator.py --help
```

## Data Generation

### How realistic is the synthetic data?

The data is **structurally realistic** but **medically simplified**:
- ✅ Valid FHIR R4 and OMOP CDM schemas
- ✅ Realistic demographics (Faker library)
- ✅ Proper concept IDs
- ⚠️ Simplified clinical relationships
- ⚠️ Not suitable for clinical validation

### Can I generate more than 100 patients?

**Yes!** Generate as many as you need:
```bash
uv run python synthetic/generators/unified_generator.py \
  --count 10000 \
  --fhir-dir ./output/fhir \
  --omop-dir ./output/omop
```

**Note**: Large datasets (>10,000 patients) may take several minutes.

### How do I add custom conditions?

Edit `synthetic/generators/unified_generator.py`:
```python
self.condition_concepts = [
    (201826, 'Type 2 Diabetes'),
    (320128, 'Essential Hypertension'),
    (317009, 'Asthma'),
    (YOUR_CONCEPT_ID, 'Your Condition Name')  # Add here
]
```

## dbt Questions

### Why does dbt use DuckDB locally?

DuckDB allows you to:
- Test dbt models without AWS
- Iterate quickly during development
- Avoid AWS costs during testing

For production, switch to Athena profile.

### How do I add a new dbt model?

1. Create file in `dbt/fhir_omop_dbt/models/marts/`:
```sql
-- my_new_model.sql
SELECT
  person_id,
  COUNT(*) as condition_count
FROM {{ ref('stg_condition_occurrence') }}
GROUP BY person_id
```

2. Run dbt:
```bash
dbt run --profiles-dir . --target dev --select my_new_model
```

### What is PIPELINE_RUN_ID?

`PIPELINE_RUN_ID` is a unique identifier for each pipeline execution, used for:
- Lineage tracking
- Debugging
- Data versioning

It flows from Step Functions → ECS tasks → dbt models.

## AWS Deployment

### How much does AWS deployment cost?

**Estimated monthly cost** (100 patients/day):
- S3: ~$1
- Athena: ~$5
- ECS Fargate: ~$10
- VPC Endpoints: ~$15
- Other: ~$2
- **Total**: ~$33/month

**Cost reduction tips:**
- Remove VPC endpoints if not needed
- Use smaller datasets
- Delete old data regularly

### Do I need a VPC?

**Yes**, the CDK stack creates a VPC for:
- Private networking
- VPC endpoints (S3, Glue, Athena)
- Security isolation

You can modify the stack to use an existing VPC.

### Can I deploy to multiple regions?

**Yes**, but you'll need to:
1. Update `cdk.json` with region
2. Bootstrap CDK in new region
3. Push container images to new region's ECR
4. Deploy stack

### How do I delete everything?

```bash
cd cdk
npx cdk destroy
```

**Warning**: This deletes all data! Backup first if needed.

## Troubleshooting

### "ModuleNotFoundError: No module named 'synthetic'"

**Solution**:
```bash
uv sync
```

### dbt compilation fails

**Common causes**:
1. Missing dependencies: `dbt deps --profiles-dir .`
2. Wrong profile: Use `--target dev` for local
3. Corrupted database: `rm target/dev.duckdb`

### Cross-model validation fails

**Common causes**:
1. FHIR and OMOP from different runs (use same seed)
2. Missing files (check paths)
3. Data corruption (regenerate)

### AWS deployment fails with "Insufficient permissions"

**Solution**: Verify IAM permissions. The deploying user needs:
- CloudFormation full access
- S3, Glue, Athena, ECS, Step Functions permissions
- VPC, KMS, IAM permissions

See [AWS Deployment Guide](deployment/AWS_DEPLOYMENT.md) for details.

### ECS tasks fail to start

**Common causes**:
1. Container images not in ECR
2. Task role missing permissions
3. VPC/subnet configuration issues

**Debug**:
```bash
aws ecs describe-tasks --cluster <cluster-name> --tasks <task-arn>
```

## Development

### How do I contribute?

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests: `./scripts/smoke-test.sh`
5. Submit pull request

### How do I run tests?

```bash
# Python unit tests
uv run pytest tests/ -v

# Integration test
./scripts/smoke-test.sh

# CDK tests
cd cdk && npm test
```

### Can I use this for my project?

**Yes!** This project is MIT licensed. You can:
- Use it as-is
- Modify for your needs
- Use in commercial projects
- Fork and customize

**Please**:
- Keep the license
- Attribute the original project
- Share improvements (optional but appreciated)

## Advanced Topics

### How does lineage tracking work?

1. Step Functions creates execution with unique ID
2. ID passed to ECS tasks as `PIPELINE_RUN_ID`
3. Synthetic pipeline uses ID for S3 paths
4. dbt accesses ID via `env_var('PIPELINE_RUN_ID')`
5. ID stored in `lineage_pipeline_run_id` column

### Can I add more FHIR resources?

**Yes!** Extend `fhir_generator.py`:
```python
def generate_observation(self, patient_id):
    return {
        "resourceType": "Observation",
        "subject": {"reference": f"Patient/{patient_id}"},
        # ... more fields
    }
```

### How do I customize dbt macros?

Edit `dbt/fhir_omop_dbt/macros/lineage.sql`:
```sql
{% macro lineage_standard_columns() %}
  -- Add custom lineage columns here
{% endmacro %}
```

## Still Have Questions?

- **GitHub Issues**: [Report bugs or ask questions](https://github.com/robandrewford/synthetic-healthlake/issues)
- **Documentation**: Check other docs in `docs/`
- **Code**: Review inline comments in source files

## Related Resources

- [FHIR Specification](https://www.hl7.org/fhir/)
- [OMOP CDM](https://ohdsi.github.io/CommonDataModel/)
- [dbt Documentation](https://docs.getdbt.com/)
- [AWS CDK Guide](https://docs.aws.amazon.com/cdk/)
- [Apache Iceberg](https://iceberg.apache.org/)
