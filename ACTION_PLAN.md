# Action Plan: 100% Complete Reference Architecture

**Goal**: Transform synthetic-healthlake into a complete, working reference architecture for learning and prototyping FHIR-OMOP data pipelines on AWS.

**Target Audience**: Healthcare data engineers, students, prototypers
**Completion Criteria**: End-to-end working pipeline with comprehensive examples and documentation

---

## Phase 1: Fix Critical Bugs & Dependencies
**Duration**: 1-2 days
**Priority**: Critical - Blocks all other work

### Tasks:

- [ ] **1.1 Fix Python Syntax Error**
  - File: `synthetic/scripts/apply_domain_constraints.py:16`
  - Change: `'--distributions-config"` → `'--distributions-config'`
  - Test: Run `python synthetic/scripts/apply_domain_constraints.py --help`

- [ ] **1.2 Complete Python Dependencies**
  - File: `pyproject.toml`
  - Add dependencies:
    ```toml
    dependencies = [
        "duckdb>=1.4.2",
        "ruff>=0.14.7",
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "faker>=20.0.0",  # for synthetic data generation
        "pyarrow>=14.0.0",  # for parquet/iceberg
        "boto3>=1.34.0",  # AWS SDK
        "click>=8.1.0",  # CLI framework
    ]
    ```
  - Test: `uv sync` and verify all imports work

- [ ] **1.3 Add Missing dbt Model**
  - File: `dbt/fhir_omop_dbt/models/staging/stg_person.sql`
  - Create staging model for OMOP person table
  - Reference: Use same pattern as `stg_fhir_patient.sql`

- [ ] **1.4 Fix pyproject.toml Metadata**
  - Update description, authors, license
  - Add project URLs (repository, documentation)

### Acceptance Criteria:
✅ All Python scripts run without syntax errors
✅ All dependencies install cleanly
✅ dbt project compiles without errors

---

## Phase 2: Complete Infrastructure Foundation
**Duration**: 3-4 days
**Priority**: High - Required for deployment

### Tasks:

- [ ] **2.1 Add KMS Encryption**
  - File: `cdk/lib/fhir-omop-stack.ts`
  - Create KMS key for data encryption
  - Update S3 bucket to use KMS encryption
  - Grant ECS tasks decrypt permissions

- [ ] **2.2 Add VPC Endpoints**
  - Add S3 Gateway Endpoint
  - Add Interface Endpoints:
    - Glue
    - Athena
    - CloudWatch Logs
    - ECR (for container pulls)
  - Associate with private subnets

- [ ] **2.3 Implement Step Functions Pipeline**
  - Create new file: `cdk/lib/step-functions-pipeline.ts`
  - Define state machine with tasks:
    1. Generate Synthetic Data (ECS Task)
    2. Flatten FHIR (ECS Task)
    3. Convert OMOP to Parquet (ECS Task)
    4. Run dbt (ECS Task)
  - Add error handling and retries
  - Export state machine ARN

- [ ] **2.4 Parameterize Container Images**
  - Add CDK context for container registry
  - Update task definitions to use parameters
  - Document how to build and push images

- [ ] **2.5 Add IAM Least Privilege**
  - Create separate task roles for each pipeline stage
  - Use path-based S3 permissions
  - Document IAM structure

- [ ] **2.6 Add Security Groups**
  - Create security group for ECS tasks
  - Restrict egress to only required endpoints
  - Document security group rules

- [ ] **2.7 Add Basic Monitoring**
  - CloudWatch Log Groups with proper retention
  - Basic CloudWatch Alarms:
    - ECS task failures
    - Step Functions execution failures
  - SNS topic for notifications (optional)

- [ ] **2.8 Add Resource Tagging**
  - Define tagging strategy
  - Apply tags to all resources:
    - Project: fhir-omop-reference
    - Environment: dev/staging/prod
    - ManagedBy: CDK

### Acceptance Criteria:
✅ `cdk synth` generates valid CloudFormation
✅ `cdk deploy` succeeds in clean AWS account
✅ All security requirements from docs/security/security.md met
✅ Infrastructure documented in README

---

## Phase 3: Implement Core Application Logic
**Duration**: 5-7 days
**Priority**: High - Core functionality

### Tasks:

- [ ] **3.1 Implement Synthetic Data Generators**
  - Create `synthetic/generators/fhir_generator.py`
    - Generate synthetic FHIR Patient resources
    - Use Faker for realistic data
    - Output to JSON/NDJSON
  - Create `synthetic/generators/omop_generator.py`
    - Generate synthetic OMOP Person, Condition, Measurement
    - Link to FHIR via person_id
    - Output to CSV/Parquet
  - Add CLI interface using Click
  - Write to S3 or local filesystem (configurable)

- [ ] **3.2 Implement Domain Constraints**
  - File: `synthetic/scripts/apply_domain_constraints.py`
  - Load constraint YAML configs
  - Validate generated data against constraints:
    - Age ranges (0-120)
    - Valid gender codes
    - Valid concept IDs
  - Apply distribution profiles (realistic age/gender distributions)
  - Document constraint YAML format

- [ ] **3.3 Implement Cross-Model Validation**
  - File: `synthetic/scripts/validate_cross_model.py`
  - Verify FHIR Patient.id matches OMOP person_id
  - Check date consistency (birth dates)
  - Validate concept mappings
  - Generate validation report

- [ ] **3.4 Create FHIR Flattening Script**
  - File: `synthetic/etl/flatten_fhir.py`
  - Read FHIR JSON bundles
  - Flatten to tabular format (Parquet)
  - Write to S3 with Iceberg metadata

- [ ] **3.5 Create OMOP Parquet Converter**
  - File: `synthetic/etl/omop_to_parquet.py`
  - Read OMOP CSV files
  - Convert to Parquet with proper schema
  - Write to S3 with Iceberg metadata

- [ ] **3.6 Add Terminology Support**
  - Create `synthetic/terminology/` directory
  - Add sample terminology files:
    - `gender_codes.yaml`
    - `condition_concepts.yaml`
  - Load in generators for realistic coding

- [ ] **3.7 Implement Configuration Management**
  - Create `synthetic/config/` directory
  - Add example configs:
    - `constraints.yaml` - domain constraints
    - `distributions.yaml` - statistical distributions
    - `pipeline.yaml` - pipeline parameters
  - Load configs in scripts

### Acceptance Criteria:
✅ Generate 1000 synthetic patients end-to-end
✅ Data passes all validation checks
✅ Scripts can run locally and in ECS
✅ Clear CLI help messages and examples

---

## Phase 4: Wire Up End-to-End Pipeline
**Duration**: 3-4 days
**Priority**: High - Integration

### Tasks:

- [ ] **4.1 Update Iceberg DDL Scripts**
  - Replace `s3://your-fhir-omop-bucket` with CDK output reference
  - Add all required columns (match staging models)
  - Add proper partitioning strategy
  - Add Iceberg table properties (compression, etc.)

- [ ] **4.2 Complete dbt Models**
  - Add missing `stg_person.sql`
  - Add `stg_person.yml` with schema documentation
  - Add missing source columns in DDL
  - Create macro: `macros/lineage_standard_columns.sql`
  - Wire pipeline_run_id from environment variable

- [ ] **4.3 Create dbt Seeds**
  - File: `dbt/fhir_omop_dbt/seeds/chronic_condition_concepts.csv`
  - Add example concept mappings
  - Document seed data purpose

- [ ] **4.4 Build Container Images**
  - Create `docker/synthetic-generator/Dockerfile`
  - Create `docker/dbt-runner/Dockerfile`
  - Add docker-compose.yml for local testing
  - Document build process in README

- [ ] **4.5 Create ECS Task Scripts**
  - File: `scripts/run_synthetic_pipeline.sh`
  - Wrapper script for ECS that:
    1. Generates data
    2. Applies constraints
    3. Validates cross-model
    4. Uploads to S3
  - File: `scripts/run_dbt_pipeline.sh`
  - Wrapper for dbt that sets PIPELINE_RUN_ID

- [ ] **4.6 Create Step Functions Integration**
  - Update state machine to pass parameters between steps
  - Add S3 path conventions (s3://bucket/runs/{run_id}/)
  - Wire PIPELINE_RUN_ID from Step Functions execution ID

- [ ] **4.7 Add Pipeline Smoke Test**
  - Update `.github/workflows/synthetic-smoke.yml`
  - Run minimal pipeline (10 patients)
  - Verify output files created
  - Run in GitHub Actions

### Acceptance Criteria:
✅ Complete pipeline runs end-to-end locally
✅ Complete pipeline runs in AWS via Step Functions
✅ Data flows from synthetic → S3 → Iceberg → dbt → Athena
✅ Can query results in Athena console

---

## Phase 5: Add Testing & Validation Examples
**Duration**: 3-4 days
**Priority**: Medium - Quality & Learning

### Tasks:

- [ ] **5.1 Add Python Unit Tests**
  - Create `tests/` directory structure
  - Add `tests/test_generators.py`
    - Test FHIR patient generation
    - Test OMOP person generation
  - Add `tests/test_validation.py`
    - Test constraint validation
    - Test cross-model validation
  - Configure pytest in pyproject.toml
  - Add test fixtures

- [ ] **5.2 Add CDK Tests**
  - Create `cdk/test/` directory
  - Add `cdk/test/stack.test.ts`
  - Test snapshot of stack
  - Test resource properties (encryption, vpc endpoints)
  - Add to package.json scripts

- [ ] **5.3 Add dbt Tests**
  - Add schema tests to all models:
    - `unique` on primary keys
    - `not_null` on required fields
    - `relationships` between models
  - Add data tests:
    - Valid date ranges
    - Valid concept IDs
  - Add custom schema tests in `tests/`

- [ ] **5.4 Add Data Quality Examples**
  - Create `dbt/fhir_omop_dbt/models/quality/` directory
  - Add data quality check models:
    - `data_quality_patient_completeness.sql`
    - `data_quality_concept_validity.sql`
  - Document data quality patterns

- [ ] **5.5 Update GitHub Actions Workflows**
  - Add Python test workflow
  - Add CDK test workflow
  - Keep dbt test workflow
  - Add test coverage reporting

- [ ] **5.6 Add Integration Test**
  - Create `tests/integration/test_full_pipeline.py`
  - Use DuckDB to simulate full pipeline locally
  - Verify data transformations end-to-end

### Acceptance Criteria:
✅ All tests pass in CI/CD
✅ Test coverage > 70% for Python code
✅ dbt tests demonstrate common patterns
✅ Clear examples for learners to follow

---

## Phase 6: Enhance Documentation & Developer Experience
**Duration**: 4-5 days
**Priority**: High - Critical for learning/prototyping

### Tasks:

- [ ] **6.1 Fix README**
  - Replace HTML comments with proper markdown code blocks
  - Add Prerequisites section:
    - AWS CLI v2
    - Node.js 20+
    - Python 3.11+
    - uv or pip
    - Docker (optional)
  - Add Architecture Diagram (simple text diagram or mermaid)
  - Add Troubleshooting section
  - Fix quickstart commands

- [ ] **6.2 Create Local Development Guide**
  - File: `docs/development/local-setup.md`
  - How to run generators locally
  - How to use DuckDB instead of Athena
  - How to test dbt models locally
  - Docker compose setup

- [ ] **6.3 Create Deployment Guide**
  - File: `docs/deployment/aws-deployment.md`
  - AWS account prerequisites
  - IAM permissions needed
  - Step-by-step CDK deployment
  - How to trigger pipeline
  - How to query results

- [ ] **6.4 Create Architecture Diagrams**
  - Create `docs/diagrams/` directory
  - Add architecture diagram (use mermaid or ASCII)
  - Add data flow diagram
  - Add infrastructure diagram
  - Reference from overview.md

- [ ] **6.5 Enhance API Documentation**
  - Update `docs/reference/api-specification.md`
  - Document all Python scripts and their CLI arguments
  - Document dbt models and their purpose
  - Add usage examples

- [ ] **6.6 Create Tutorial/Walkthrough**
  - File: `docs/tutorial/getting-started.md`
  - Step-by-step tutorial:
    1. Generate synthetic data locally
    2. Validate the data
    3. Deploy to AWS
    4. Run pipeline
    5. Query results
  - Include expected outputs and screenshots

- [ ] **6.7 Add Code Examples**
  - Create `examples/` directory
  - Add `examples/query_athena.py` - Query results programmatically
  - Add `examples/custom_generator.py` - Extend generators
  - Add `examples/custom_dbt_model.sql` - Add new model

- [ ] **6.8 Improve Inline Documentation**
  - Add docstrings to all Python functions
  - Add comments to dbt models explaining logic
  - Add comments to CDK constructs
  - Add type hints everywhere

- [ ] **6.9 Create FAQ**
  - File: `docs/FAQ.md`
  - Common questions about setup, errors, usage
  - Link from README

- [ ] **6.10 Validate MkDocs Navigation**
  - Run `mkdocs serve` locally
  - Fix any navigation issues
  - Ensure all pages accessible
  - Add missing pages to nav

### Acceptance Criteria:
✅ README has clear, working quickstart
✅ New user can set up and run pipeline following docs
✅ All documentation renders correctly in MkDocs
✅ Code is well-commented and self-documenting

---

## Phase 7: Add Security Demonstrations
**Duration**: 2-3 days
**Priority**: Medium - Best practices showcase

### Tasks:

- [ ] **7.1 Add Secrets Management Example**
  - Create example using AWS Secrets Manager
  - Show how to pass secrets to ECS tasks
  - Document in `docs/security/secrets-management.md`

- [ ] **7.2 Enhance S3 Security**
  - Add bucket policy requiring HTTPS
  - Add bucket policy for encryption enforcement
  - Add lifecycle policies for cost optimization
  - Add access logging bucket (optional)

- [ ] **7.3 Add Dependency Scanning to CI**
  - Add `npm audit` to CDK workflow
  - Add `pip-audit` to Python workflow
  - Add dependabot configuration
  - Document in SECURITY.md

- [ ] **7.4 Add Security Group Documentation**
  - Document security group rules
  - Create diagram showing network boundaries
  - Add to `docs/security/network-security.md`

- [ ] **7.5 Add IAM Policy Examples**
  - Document least-privilege patterns
  - Show how to audit IAM permissions
  - Add to `docs/security/iam-best-practices.md`

- [ ] **7.6 Add GitHub Actions OIDC**
  - Replace long-lived credentials with OIDC
  - Document setup process
  - Update all workflows

- [ ] **7.7 Create Security Checklist**
  - File: `docs/security/deployment-checklist.md`
  - Pre-deployment security review checklist
  - Runtime security monitoring recommendations

### Acceptance Criteria:
✅ All documented security requirements implemented
✅ No long-lived credentials in GitHub Actions
✅ Security best practices demonstrated
✅ Security documentation comprehensive

---

## Phase 8: Polish & Validation
**Duration**: 2-3 days
**Priority**: Medium - Final touches

### Tasks:

- [ ] **8.1 Add Pre-commit Hooks**
  - File: `.pre-commit-config.yaml`
  - Add hooks:
    - ruff (linting)
    - ruff-format (formatting)
    - mypy (type checking)
    - trailing whitespace
    - yaml validation
  - Document in CONTRIBUTING.md

- [ ] **8.2 Code Quality Pass**
  - Run ruff on all Python code
  - Format all code consistently
  - Fix all type errors
  - Remove dead code

- [ ] **8.3 Infrastructure Validation**
  - Deploy to clean AWS account
  - Run complete pipeline
  - Verify all outputs
  - Document actual costs incurred

- [ ] **8.4 Create Sample Dataset**
  - Generate 10,000 patient synthetic dataset
  - Include in S3 or document how to generate
  - Add sample queries for this dataset

- [ ] **8.5 Performance Benchmarking**
  - Document pipeline performance:
    - Time to generate N patients
    - Time to run dbt transformations
    - Query performance in Athena
  - Add to `docs/operations/performance.md`

- [ ] **8.6 Cost Analysis**
  - Document actual AWS costs
  - Provide cost breakdown by service
  - Add to `docs/operations/cost-analysis.md`
  - Add cost optimization tips

- [ ] **8.7 Add Cleanup Scripts**
  - File: `scripts/cleanup.sh`
  - Safely destroy all AWS resources
  - Clear S3 buckets
  - Delete Glue tables

- [ ] **8.8 Create Video Tutorial (Optional)**
  - Record screen walkthrough
  - Upload to YouTube
  - Link from README

- [ ] **8.9 Final Documentation Review**
  - Proofread all documentation
  - Fix broken links
  - Ensure consistency
  - Update TODO.md with any remaining items

- [ ] **8.10 Create Release Checklist**
  - File: `docs/development/release-checklist.md`
  - Define what constitutes a "release"
  - Version tagging strategy
  - Changelog format

### Acceptance Criteria:
✅ Complete end-to-end pipeline runs flawlessly
✅ All documentation accurate and tested
✅ Code quality meets professional standards
✅ Ready for public sharing/learning use

---

## Success Metrics

### Functional Completeness:
- [ ] All Python scripts fully implemented (no stubs)
- [ ] All dbt models compile and run
- [ ] All CDK infrastructure deploys successfully
- [ ] End-to-end pipeline runs without errors
- [ ] Sample queries return expected results

### Documentation Quality:
- [ ] 100% of code has docstrings/comments
- [ ] All README commands tested and working
- [ ] Complete tutorial walkthrough exists
- [ ] All diagrams created and rendered
- [ ] FAQ covers common issues

### Developer Experience:
- [ ] New developer can set up locally in < 30 minutes
- [ ] New developer can deploy to AWS in < 1 hour
- [ ] Clear error messages guide troubleshooting
- [ ] Examples demonstrate all key features

### Quality Assurance:
- [ ] Python test coverage > 70%
- [ ] All dbt models have tests
- [ ] CDK infrastructure has assertions
- [ ] No linting errors
- [ ] All type hints pass mypy

### Learning Value:
- [ ] Demonstrates AWS best practices
- [ ] Shows healthcare data engineering patterns
- [ ] Includes anti-patterns to avoid
- [ ] Explains architectural decisions
- [ ] Provides extension points for learners

---

## Estimated Total Effort

**Total Duration**: 22-32 days (engineering time)
**Parallel Work Possible**: Phases 3, 5, 6 can partially overlap

### Resource Requirements:
- 1 Senior Data Engineer (infrastructure & data pipeline)
- 1 Python Developer (synthetic generators & ETL)
- 1 Technical Writer (documentation - can be part-time)

### Critical Path:
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 8

Phases 5, 6, 7 can proceed in parallel with Phase 4 completion.

---

## Risk Mitigation

### Technical Risks:
- **Iceberg table creation complexity**: Use DuckDB locally first to validate schema
- **dbt + Athena integration issues**: Follow dbt-athena-community examples closely
- **ECS task networking**: Test VPC endpoints early, have fallback to public subnets

### Documentation Risks:
- **Scope creep in documentation**: Focus on practical examples, not exhaustive reference
- **Documentation drift**: Review docs with each code change
- **Complexity**: Use progressive disclosure (quick start → deep dive)

### Testing Risks:
- **AWS integration test costs**: Use small datasets, cleanup aggressively
- **Test environment setup**: Provide terraform/CDK for test account
- **CI/CD pipeline flakiness**: Add retries, use stable AWS regions

---

## Post-Completion Enhancements

Ideas for future iterations (beyond 100% baseline):

1. **Add Observability Stack**
   - X-Ray tracing
   - CloudWatch Insights queries
   - Grafana dashboards

2. **Add More Healthcare Standards**
   - HL7 v2 messages
   - CDA documents
   - Additional OMOP tables

3. **Add ML Feature Store**
   - SageMaker Feature Store integration
   - Example ML training pipeline

4. **Add Governance Examples**
   - Lake Formation fine-grained access
   - AWS Glue Data Quality
   - Data catalog tagging

5. **Multi-Region Deployment**
   - Cross-region replication
   - Disaster recovery example

6. **Cost Optimization Mode**
   - Spot instances for ECS
   - S3 Intelligent-Tiering
   - Query result caching

7. **Advanced dbt Features**
   - Snapshots for SCDs
   - Incremental models
   - dbt metrics semantic layer

---

## Maintenance Plan

### Quarterly Updates:
- [ ] Update AWS CDK to latest version
- [ ] Update dbt to latest version
- [ ] Refresh sample data
- [ ] Review and update documentation

### Dependency Management:
- [ ] Enable Dependabot
- [ ] Review and merge security updates monthly
- [ ] Test with new Python/Node versions annually

### Community Engagement:
- [ ] Monitor GitHub issues
- [ ] Accept pull requests for improvements
- [ ] Share learnings in blog posts/talks

---

## Getting Started with This Plan

### Immediate Next Steps:

1. **Review and prioritize** this plan with stakeholders
2. **Set up project tracking** (GitHub Projects, Jira, etc.)
3. **Assign ownership** for each phase
4. **Create development branch** strategy
5. **Begin Phase 1** immediately (critical bug fixes)

### Recommended Workflow:

1. Create GitHub issues for each checkbox item
2. Label by phase and priority
3. Create pull requests referencing issues
4. Review and merge incrementally
5. Update this action plan as scope changes

### Success First Milestone:

**Target**: Complete Phases 1-4 (Core Functionality)
**Duration**: ~2 weeks
**Deliverable**: Working end-to-end pipeline with basic documentation

---

*This action plan is a living document. Update as you learn and adapt to findings.*
