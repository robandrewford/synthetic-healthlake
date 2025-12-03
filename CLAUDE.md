# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FHIR-OMOP Synthetic Stack** is an AWS-based reference architecture for generating, validating, and transforming synthetic healthcare data (FHIR + OMOP CDM) through a modern data lakehouse built on Apache Iceberg, Glue Catalog, Athena, and dbt.

**Current Status**: ~50% complete for production, ~75% complete as learning/prototyping reference architecture. See `ACTION_PLAN.md` for comprehensive completion roadmap.

**Phases Completed**:
- ✅ Phase 1: Fix Critical Bugs & Dependencies (Python syntax, dependencies, dbt models)
- ✅ Phase 2: Complete Infrastructure Foundation (KMS, VPC endpoints, Step Functions, security)
- 🚧 Phase 3: Implement Core Application Logic (in progress)

**Current Known Issues**:
- Synthetic data generators not yet implemented (stubs only)
- ETL scripts (`flatten_fhir.py`, `omop_to_parquet.py`) missing
- Validation scripts are stubs without full implementation
- Configuration files are minimal examples

## Development Commands

### Python Environment
```bash
# Install dependencies (uses uv for package management)
uv sync

# Lint Python code
ruff check .

# Format Python code
ruff format .

# Run Python scripts (currently stubs)
python synthetic/scripts/apply_domain_constraints.py --help
python synthetic/scripts/validate_cross_model.py --help
```

### CDK Infrastructure
```bash
cd cdk/

# Install dependencies
npm install

# Build TypeScript
npx tsc

# Synthesize CloudFormation
npm run synth
# or: npx cdk synth

# Deploy to AWS
cdk bootstrap  # first time only
cdk deploy

# Destroy infrastructure
cdk destroy
```

### dbt Transformations
```bash
cd dbt/fhir_omop_dbt/

# Compile models (check for errors)
dbt compile

# Load seed data
dbt seed

# Run all models
dbt run

# Run specific model
dbt run --select stg_fhir_patient
dbt run --select dim_patient

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

### Documentation
```bash
# Serve MkDocs locally
pip install mkdocs mkdocs-material
mkdocs serve

# Build static site
mkdocs build
```

## Architecture Overview

### Data Flow Pipeline (Planned)
```
Synthetic Generators → FHIR Flattening → OMOP Parquet → dbt Transformations → Athena Queries
     (Python)              (Python)          (Python)      (SQL/dbt)           (SQL)
        ↓                     ↓                  ↓              ↓
    Raw JSON/CSV    →    S3 Iceberg    →   S3 Iceberg   →  Analytics Tables
```

### Three-Layer Architecture

**1. Synthetic Data Layer** (`synthetic/`)
- **Purpose**: Generate realistic FHIR and OMOP synthetic patient data
- **Components**:
  - `synthetic/scripts/apply_domain_constraints.py` - Apply medical domain rules and distributions
  - `synthetic/scripts/validate_cross_model.py` - Validate FHIR-OMOP consistency
  - `synthetic/config/` - YAML configs for constraints, distributions, terminology
- **Status**: Stub implementations, needs full generator logic

**2. Storage & ETL Layer** (AWS)
- **Iceberg Tables**: ACID-compliant tables on S3 with Glue Catalog metadata
- **DDL Scripts**: `iceberg-ddl/*.sql` define table schemas
- **Orchestration**: Step Functions pipeline (not yet implemented) will coordinate:
  1. Synthetic data generation (ECS Fargate)
  2. FHIR flattening (ECS Fargate)
  3. OMOP conversion (ECS Fargate)
  4. dbt transformations (ECS Fargate)

**3. Transformation Layer** (`dbt/fhir_omop_dbt/`)
- **Staging Models** (`models/staging/`): Raw data from Iceberg sources
  - `stg_fhir_patient.sql` - FHIR patient staging
  - `stg_person.sql` - OMOP person staging (MISSING - needs creation)
- **Marts** (`models/marts/`): Analytics-ready dimensional/fact tables
  - `dim_patient.sql` - Patient dimension (joins FHIR + OMOP)
  - `fact_chronic_condition.sql` - Chronic condition facts
- **Metrics** (`models/metrics/`): MetricFlow-ready metric definitions
- **Macros** (`macros/`):
  - `lineage.sql` - `lineage_standard_columns()` macro for data provenance tracking
  - Expects `PIPELINE_RUN_ID` environment variable (currently hardcoded as null)

### Infrastructure Layer (`cdk/`)
- **Main Stack**: `cdk/lib/fhir-omop-stack.ts`
  - VPC with public/private subnets
  - S3 bucket for data (currently S3-managed encryption, needs KMS)
  - Glue Database catalog
  - ECS Cluster + Fargate task definitions
  - **Missing**: VPC endpoints, Step Functions, proper security groups

## Key Architectural Patterns

### Data Lineage Tracking
All dbt mart models should use the `lineage_standard_columns()` macro to track:
- Pipeline run ID (from Step Functions/ECS via `PIPELINE_RUN_ID` env var)
- Source origin (OMOP, FHIR, or combined)
- dbt run metadata (invocation_id, model name, target environment)
- Ingestion timestamps

Example usage in `dim_patient.sql`:
```sql
{{ lineage_standard_columns(
    omop_ts_col       = 'p.omop_ingestion_ts',
    fhir_ts_col       = 'f.fhir_ingestion_ts',
    synthetic_source_col = 'coalesce(f.synthetic_source, \'synthetic_unknown\')',
    pipeline_run_id_expr = "cast(null as varchar)"  -- TODO: Wire from ECS
) }}
```

### Synthetic-First Design
- **No Real Patient Data**: Only synthetic data allowed (HIPAA/compliance safe)
- Generators must respect medical domain constraints (age ranges, valid codes, realistic distributions)
- Cross-model validation ensures FHIR and OMOP representations are consistent

### Iceberg Table Strategy
- **Partitioning**: Tables partitioned by relevant date columns (e.g., `year_of_birth`)
- **Format**: Parquet with compression
- **Time Travel**: Iceberg supports historical queries
- **Schema Evolution**: Can add/modify columns without breaking queries

## Coding Standards

### Python
- Follow PEP8, use type hints
- Prefer `pathlib` over `os.path`
- Use `logging` module, not `print()` for production code
- Add error handling for file I/O and data validation

### TypeScript (CDK)
- Enable strict mode in `tsconfig.json`
- No magic numbers - use constants or CDK context
- Export constructs cleanly
- Tag all resources for cost allocation

### dbt Models
- **Naming**: Staging models prefix with `stg_*`
- **Materialization**: Staging = views, marts = tables
- **Always use**: `{{ ref() }}` for models, `{{ source() }}` for raw tables
- **Documentation**: Include `version: 2` YAML with column descriptions
- **Testing**: Add `unique`, `not_null`, `relationships` tests

### YAML Configs
- 2-space indentation
- Lowercase field names
- Separate files for constraints vs distributions vs terminology

## Important File Locations

### Configuration
- `pyproject.toml` - Python dependencies (managed by uv)
- `cdk/cdk.json` - CDK app configuration
- `dbt/fhir_omop_dbt/dbt_project.yml` - dbt project config
- `dbt/fhir_omop_dbt/profiles.example.yml` - dbt profile template for Athena

### Documentation
- `docs/` - MkDocs documentation source
- `docs/architecture/design-decisions.md` - Key architectural rationale
- `docs/security/security.md` - Security requirements and policies
- `ACTION_PLAN.md` - Detailed 8-phase completion plan (70+ tasks)
- `QUICK_CHECKLIST.md` - Progress tracking checklist
- `GETTING_STARTED.md` - Implementation guide with quick wins

### Infrastructure
- `cdk/lib/fhir-omop-stack.ts` - Main CDK stack definition
- `iceberg-ddl/*.sql` - Iceberg table DDL statements (run in Athena)

### Testing
- `.github/workflows/` - CI/CD pipelines
  - `cdk-deploy.yml` - CDK synth on push
  - `dbt-tests.yml` - dbt tests on PR (uses AWS credentials in secrets)
  - `synthetic-smoke.yml` - Smoke tests for generators

## Critical Context for Development

### Known Gaps Requiring Implementation
1. **Synthetic generators are stubs** - Need full implementation using Faker, medical terminologies
2. **Step Functions orchestration missing** - Pipeline coordination not yet built
3. **PIPELINE_RUN_ID wiring** - Currently hardcoded as null, needs ECS/Step Functions integration
4. **Security hardening incomplete**:
   - Missing KMS encryption for S3
   - Missing VPC endpoints (S3, Glue, Athena, CloudWatch, ECR)
   - Missing security groups for ECS tasks
   - Long-lived AWS credentials in GitHub Actions (should use OIDC)
5. **No test coverage** - No pytest tests, no CDK tests, minimal dbt tests

### Design Decisions to Respect
- **Iceberg over Delta Lake**: Chosen for Athena compatibility and ACID guarantees
- **ECS Fargate over Lambda**: Batch processing can exceed Lambda limits
- **dbt over Spark**: SQL-first approach, simpler for analytics teams
- **Step Functions over Airflow**: Serverless, AWS-native orchestration
- **Synthetic-only data**: Non-negotiable for compliance and safety

### When Modifying dbt Models
- Ensure `stg_person.sql` references `source('omop', 'person_iceberg')`
- Mart models joining FHIR + OMOP must handle null/missing joins gracefully
- Always include lineage columns via `lineage_standard_columns()` macro
- Test with: `dbt compile` before `dbt run`

### When Modifying CDK Infrastructure
- All resources must have encryption at rest (KMS preferred)
- All resources must have tags: Project, Environment, ManagedBy
- ECS tasks must run in private subnets with VPC endpoints
- Use least-privilege IAM (path-based S3 permissions, not bucket-wide)
- Test with: `npm run build && npx cdk synth`

### When Adding Python Scripts
- Add to `pyproject.toml` dependencies if new packages needed
- Use `click` for CLI interfaces
- Write to S3 using `boto3` with proper error handling
- Support both local filesystem and S3 paths via configuration

## Environment Variables

### dbt Runtime
- `PIPELINE_RUN_ID` - Unique identifier for pipeline execution (passed from Step Functions)
- `DBT_TARGET` - Target environment (dev/prod)
- AWS credentials for Athena access

### ECS Tasks (Future)
- `S3_DATA_BUCKET` - Target S3 bucket for outputs
- `GLUE_DB_NAME` - Glue database name
- `PIPELINE_RUN_ID` - Execution identifier
- AWS role-based credentials (no keys)

## Reference Documentation

**Primary Planning Docs**:
- `ACTION_PLAN.md` - Start here for understanding completion roadmap
- `GETTING_STARTED.md` - Step-by-step guide to begin implementation
- `IMPLEMENTATION_SUMMARY.md` - Executive overview and timelines

**Technical Docs**:
- `docs/architecture/overview.md` - High-level system architecture
- `docs/data/validation-framework.md` - Data quality approach
- `docs/operations/observability-plan.md` - Monitoring strategy

**Healthcare Standards**:
- FHIR R4 for patient resources
- OMOP CDM 5.x for observational medical data
- Concept IDs must be valid OMOP standard concepts

## Common Workflows

### Adding a New dbt Model
1. Create `.sql` file in appropriate directory (`staging/` or `marts/`)
2. Create corresponding `.yml` with schema and tests
3. Use `{{ ref() }}` for dependencies, `{{ source() }}` for raw tables
4. Include `{{ lineage_standard_columns() }}` in marts
5. Run `dbt compile` to check for errors
6. Run `dbt run --select your_model` to execute
7. Add tests: `unique`, `not_null`, `relationships`

### Deploying Infrastructure Changes
1. Modify TypeScript in `cdk/lib/`
2. Run `npm run build` to compile
3. Run `npx cdk synth` to generate CloudFormation
4. Review diff: `npx cdk diff`
5. Deploy: `cdk deploy`
6. Verify in AWS Console

### Testing Synthetic Data Generators
1. Fix syntax error in `apply_domain_constraints.py` first
2. Add missing dependencies to `pyproject.toml`
3. Run `uv sync`
4. Test locally before deploying to ECS
5. Use small datasets (10-100 patients) for testing
6. Validate output against constraints YAML

## Security Considerations

- **Never commit real patient data** (synthetic only)
- **Never commit AWS credentials** (use IAM roles, OIDC)
- **Always encrypt data at rest** (KMS for S3, EBS)
- **Always encrypt data in transit** (HTTPS/TLS)
- Run `npm audit` for CDK dependencies
- Run `pip-audit` for Python dependencies (add to CI)
- All ECS tasks should use private subnets with VPC endpoints
- S3 buckets must have `BlockPublicAccess` enabled

## Troubleshooting

### dbt compilation fails with missing model
- Likely `stg_person.sql` is missing - create it following `stg_fhir_patient.sql` pattern
- Check `sources_fhir_omop.yml` for correct source table names

### CDK synth fails
- Run `npm run build` first to compile TypeScript
- Check for missing imports or typos in construct properties

### Python import errors
- Run `uv sync` to install missing dependencies
- Check syntax in scripts (known error on line 16 of `apply_domain_constraints.py`)

### Athena queries fail on Iceberg tables
- Verify tables created with DDL in `iceberg-ddl/*.sql`
- Check S3 bucket paths match CDK outputs
- Ensure Glue Catalog database exists

### GitHub Actions workflows fail
- Check AWS credentials are set in repository secrets
- Workflows expect `ATHENA_S3_STAGING_DIR`, `AWS_REGION`, AWS access keys
- Long-term: migrate to OIDC for GitHub Actions (see ACTION_PLAN.md Phase 7.6)
