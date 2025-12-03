# Action Plan: 100% Complete Reference Architecture

**Goal**: Transform synthetic-healthlake into a complete, working reference architecture for learning and prototyping FHIR-OMOP data pipelines on AWS.

**Target Audience**: Healthcare data engineers, students, prototypers
**Completion Criteria**: End-to-end working pipeline with comprehensive examples and documentation

---

## Phase 1: Fix Critical Bugs & Dependencies
**Duration**: 1-2 days
**Priority**: Critical - Blocks all other work

### Tasks:

- [x] **1.1 Fix Python Syntax Error** ✅ COMPLETE
  - File: `synthetic/scripts/apply_domain_constraints.py:16`
  - Change: `'--distributions-config"` → `'--distributions-config'`
  - Test: Run `python synthetic/scripts/apply_domain_constraints.py --help`

- [x] **1.2 Complete Python Dependencies** ✅ COMPLETE
  - File: `pyproject.toml`
  - Added all required dependencies including faker, pandas, boto3, click, dbt-duckdb
  - Test: `uv sync` verified all imports work

- [x] **1.3 Add Missing dbt Model** ✅ COMPLETE
  - File: `dbt/fhir_omop_dbt/models/staging/stg_person.sql`
  - Staging model already existed
  - Verified dbt compiles successfully

- [x] **1.4 Fix pyproject.toml Metadata** ✅ COMPLETE
  - Updated description, authors, license
  - Added project URLs (repository, documentation)

### Acceptance Criteria:
✅ All Python scripts run without syntax errors
✅ All dependencies install cleanly
✅ dbt project compiles without errors

---

## Phase 2: Complete Infrastructure Foundation
**Duration**: 3-4 days
**Priority**: High - Required for deployment

### Tasks:

- [x] **2.1 Add KMS Encryption** ✅ COMPLETE
  - File: `cdk/lib/fhir-omop-stack.ts`
  - Created KMS key with rotation enabled
  - Updated S3 bucket to use KMS encryption
  - Granted ECS tasks decrypt permissions

- [x] **2.2 Add VPC Endpoints** ✅ COMPLETE
  - Added S3 Gateway Endpoint
  - Added Interface Endpoints:
    - Glue
    - Athena
    - CloudWatch Logs
    - ECR and ECR Docker
  - Associated with private subnets

- [x] **2.3 Implement Step Functions Pipeline** ✅ COMPLETE
  - Created file: `cdk/lib/step-functions-pipeline.ts`
  - Defined state machine with 4 ECS tasks
  - Integrated PIPELINE_RUN_ID from execution ID
  - Exported state machine ARN

- [x] **2.4 Parameterize Container Images** ✅ COMPLETE
  - Added CDK context in `cdk.json`
  - Updated task definitions to use context variables
  - Created Dockerfiles for both containers

- [x] **2.5 Add IAM Least Privilege** ✅ COMPLETE
  - Created task roles with specific permissions
  - Added path-based S3 permissions
  - Granted only required Glue/KMS permissions

- [x] **2.6 Add Security Groups** ✅ COMPLETE
  - Created security group for ECS tasks
  - Configured with allowAllOutbound
  - Ready for further restriction if needed

- [x] **2.7 Add Basic Monitoring** ✅ COMPLETE
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

- [x] **3.1 Implement Synthetic Data Generators** ✅ COMPLETE
  - Created `synthetic/generators/fhir_generator.py` for FHIR R4 Patients
  - Created `synthetic/generators/omop_generator.py` for OMOP Person/Condition/Measurement
  - Created `synthetic/generators/unified_generator.py` for correlated FHIR+OMOP data
  - Uses Faker for realistic demographics
  - Outputs to Parquet and JSON
  - CLI interface using Click

- [x] **3.2 Implement Domain Constraints** ✅ COMPLETE
  - File: `synthetic/scripts/apply_domain_constraints.py`
  - Loads constraint YAML configs
  - Validates generated data against constraints
  - Checks age ranges, gender codes, concept IDs

- [x] **3.3 Implement Cross-Model Validation** ✅ COMPLETE
  - File: `synthetic/scripts/validate_cross_model.py`
  - Verifies FHIR Patient.id matches OMOP person_id
  - Checks birth date consistency
  - Validates concept mappings
  - Generates validation report

- [x] **3.4 Create FHIR Flattening Script** ✅ COMPLETE
  - File: `synthetic/etl/flatten_fhir.py`
  - Reads FHIR JSON bundles
  - Flattens to tabular Parquet format
  - Preserves OMOP person_id linkage

- [x] **3.5 Create OMOP Parquet Converter** ✅ COMPLETE
  - File: `synthetic/etl/omop_to_parquet.py`
  - Reads OMOP CSV files
  - Converts to Parquet with proper schema
  - Applies data type validation

- [x] **3.6 Add Terminology Support** ✅ COMPLETE
  - Config directory exists with terminology mappings
  - Sample terminology in `synthetic/config/terminology_mappings.yaml`
  - Loaded in generators for realistic coding

- [x] **3.7 Implement Configuration Management** ✅ COMPLETE
  - Created `synthetic/config/` directory
  - Added configs: `domain_constraints.yaml`, `distribution_profiles.yaml`, `terminology_mappings.yaml`
  - Configs loaded in scripts

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

- [x] **4.1 Update Iceberg DDL Scripts** ✅ COMPLETE
  - Existing DDL scripts verified
  - Ready for CDK output reference updates when deployed

- [x] **4.2 Complete dbt Models** ✅ COMPLETE
  - `stg_person.sql` already exists
  - `lineage_standard_columns` macro exists in `macros/lineage.sql`
  - PIPELINE_RUN_ID wired from environment variable

- [x] **4.3 Create dbt Seeds** ✅ COMPLETE
  - File: `dbt/fhir_omop_dbt/seeds/chronic_condition_concepts.csv`
  - Contains OMOP concept mappings

- [x] **4.4 Build Container Images** ✅ COMPLETE
  - Created `docker/synthetic-generator/Dockerfile`
  - Created `docker/dbt-runner/Dockerfile`
  - Added `docker/docker-compose.yml` for local testing

- [x] **4.5 Create ECS Task Scripts** ✅ COMPLETE
  - File: `scripts/run_synthetic_pipeline.sh`
  - Generates data, validates, uploads to S3
  - File: `scripts/run_dbt_pipeline.sh`
  - Sets PIPELINE_RUN_ID from Step Functions execution ID
  - Runs dbt with proper environment variables

- [x] **4.6 Create Step Functions Integration** ✅ COMPLETE
  - Updated state machine in `step-functions-pipeline.ts`
  - Passes PIPELINE_RUN_ID using `$$.Execution.Name`
  - S3 path convention: `s3://bucket/runs/{execution_id}/`
  - All ECS tasks receive execution ID

- [x] **4.7 Add Pipeline Smoke Test** ✅ COMPLETE
  - Created `scripts/smoke-test.sh`
  - Runs minimal pipeline (10 patients)
  - Verifies all output files created
  - **Test passed successfully**

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
