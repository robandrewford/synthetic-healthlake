# Getting Started with the Action Plan

This guide helps you begin implementing the ACTION_PLAN.md to achieve 100% completion.

## Prerequisites

### Install Beads CLI

This project uses `bd` (beads) for issue tracking. Install it first:

```bash
# Quick install (macOS/Linux)
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Verify installation
bd --version
bd status
```

**See [docs/development/beads-installation.md](docs/development/beads-installation.md) for detailed installation instructions and troubleshooting.**

## Step 1: Set Up Project Tracking

### Option A: GitHub Projects (Recommended)

1. Go to your repository on GitHub
2. Click "Projects" tab → "New project"
3. Choose "Board" template
4. Create columns:
   - 🆕 To Do
   - 🏃 In Progress
   - 👀 In Review
   - ✅ Done
   - ⏸️ Blocked

5. Create labels:
   ```
   phase-1-critical (red)
   phase-2-infra (orange)
   phase-3-application (yellow)
   phase-4-pipeline (green)
   phase-5-testing (blue)
   phase-6-docs (purple)
   phase-7-security (pink)
   phase-8-polish (gray)
   ```

6. Create issues for each task in ACTION_PLAN.md using the template in `.github/ISSUE_TEMPLATE/phase-task.md`

### Option B: Local Tracking

Use QUICK_CHECKLIST.md and check off items as you complete them.

## Step 2: Start with Quick Wins (30 minutes)

These build momentum and are easy to complete:

### Fix 1: Python Syntax Error (5 min)

```bash
# Open the file
code synthetic/scripts/apply_domain_constraints.py

# Line 16: Change this:
parser.add_argument('--distributions-config", required=True)

# To this:
parser.add_argument('--distributions-config', required=True)

# Verify
python synthetic/scripts/apply_domain_constraints.py --help
```

### Fix 2: Update pyproject.toml (10 min)

```bash
code pyproject.toml
```

Replace the dependencies section:

```toml
[project]
name = "synthetic-healthlake"
version = "0.1.0"
description = "AWS reference architecture for FHIR-OMOP synthetic healthcare data pipelines"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
license = {text = "MIT"}
dependencies = [
    "duckdb>=1.4.2",
    "ruff>=0.14.7",
    "pyyaml>=6.0",
    "pandas>=2.0.0",
    "faker>=20.0.0",
    "pyarrow>=14.0.0",
    "boto3>=1.34.0",
    "click>=8.1.0",
]

[project.urls]
Repository = "https://github.com/yourusername/synthetic-healthlake"
Documentation = "https://yourusername.github.io/synthetic-healthlake"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

Then install:

```bash
uv sync
```

### Fix 3: Fix README Code Blocks (10 min)

```bash
code README.md
```

Change lines 43-62 from:

```markdown
<!-- 1. Deploy CDK -->
cd cdk/
npm install
```

To proper markdown code blocks:

````markdown
## Quickstart

### 1. Deploy CDK Infrastructure

```bash
cd cdk/
npm install
cdk bootstrap
cdk deploy
```

### 2. Run Synthetic Pipeline

```bash
aws stepfunctions start-execution \
  --state-machine-arn <your-sm-arn>
```

### 3. Run dbt Transformations

```bash
cd dbt/fhir_omop_dbt/
dbt seed
dbt run
dbt test
```

### 4. Query Results in Athena

```sql
SELECT * FROM fhir_omop_dbt.dim_patient LIMIT 10;
```
````

### Fix 4: Create Missing dbt Model (10 min)

```bash
# Create the file
touch dbt/fhir_omop_dbt/models/staging/stg_person.sql
code dbt/fhir_omop_dbt/models/staging/stg_person.sql
```

Add this content:

```sql
{{ config(materialized='view') }}

with source as (
    select
        person_id,
        gender_concept_id,
        year_of_birth,
        month_of_birth,
        day_of_birth,
        birth_datetime,
        race_concept_id,
        ethnicity_concept_id,
        person_source_value,
        gender_source_value,
        race_source_value,
        ethnicity_source_value,
        ingestion_timestamp as _ingestion_ts
    from {{ source('omop', 'person_iceberg') }}
)
select * from source
```

Create the YAML:

```bash
touch dbt/fhir_omop_dbt/models/staging/stg_person.yml
code dbt/fhir_omop_dbt/models/staging/stg_person.yml
```

```yaml
version: 2

models:
  - name: stg_person
    description: Staging model for OMOP CDM Person table
    columns:
      - name: person_id
        description: Unique identifier for person
        tests:
          - unique
          - not_null
      - name: gender_concept_id
        description: OMOP concept ID for gender
      - name: birth_datetime
        description: Date and time of birth
```

**✅ Checkpoint**: Verify dbt compiles

```bash
cd dbt/fhir_omop_dbt/
dbt compile
```

## Step 3: Create Your Development Branch

```bash
git checkout -b feature/action-plan-implementation
git add .
git commit -m "feat: Initial fixes - syntax, dependencies, README, stg_person

- Fix syntax error in apply_domain_constraints.py
- Add complete Python dependencies to pyproject.toml
- Fix README code blocks formatting
- Create missing stg_person.sql dbt model

Progress: Phase 1 tasks 1.1, 1.2, 1.3, 1.4 complete"

git push -u origin feature/action-plan-implementation
```

## Step 4: Set Up Local Development Environment

### Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Create config
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
EOF

# Install hooks
pre-commit install
```

### Test Local Generation (Prepare for Phase 3)

```bash
# Create a simple test script
cat > test_local.py << 'EOF'
#!/usr/bin/env python3
"""Quick test that environment is working"""

import duckdb
import pandas as pd
import yaml
from faker import Faker

print("✅ All imports successful!")
print(f"DuckDB version: {duckdb.__version__}")
print(f"Pandas version: {pd.__version__}")

# Test Faker
fake = Faker()
print(f"Sample name: {fake.name()}")
print(f"Sample birthdate: {fake.date_of_birth()}")
EOF

python test_local.py
```

## Step 5: Begin Phase 2 (Infrastructure)

Create a new branch for infrastructure work:

```bash
git checkout -b feature/phase-2-infrastructure
```

### Task 2.1: Add KMS Encryption

Edit `cdk/lib/fhir-omop-stack.ts`:

```typescript
import * as kms from 'aws-cdk-lib/aws-kms';

// Add after line 12 in constructor:
const dataKey = new kms.Key(this, 'FhirOmopDataKey', {
  enableKeyRotation: true,
  description: 'KMS key for FHIR-OMOP data encryption',
  alias: 'fhir-omop-data'
});

// Update dataBucket (replace lines 23-27):
const dataBucket = new s3.Bucket(this, 'FhirOmopDataBucket', {
  versioned: true,
  encryption: s3.BucketEncryption.KMS,
  encryptionKey: dataKey,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  enforceSSL: true,  // Require HTTPS
});

// Grant ECS tasks decrypt permission (after line 42):
dataKey.grantEncryptDecrypt(taskRole);
```

Test:

```bash
cd cdk/
npm run build
npx cdk synth
```

## Step 6: Track Your Progress

Update QUICK_CHECKLIST.md as you go:

```bash
# Mark items complete
code QUICK_CHECKLIST.md

# Update progress section at bottom
**Phases Complete**: 1 / 8  ← Update this
**Tasks Complete**: 4 / 70+  ← Update this
```

## Step 7: Commit Frequently

Use conventional commit messages:

```bash
# Examples:
git commit -m "feat(cdk): add KMS encryption to S3 bucket"
git commit -m "fix(python): correct argument syntax in apply_domain_constraints"
git commit -m "docs(readme): fix code block formatting"
git commit -m "test(dbt): add schema tests to stg_person"
```

## Step 8: Create Pull Requests

When you complete a phase or significant milestone:

```bash
# Push your branch
git push

# Create PR on GitHub with:
# Title: "[Phase X] Description"
# Body: Link to specific section of ACTION_PLAN.md
# Checklist of completed tasks
```

---

## Recommended Order of Execution

### Week 1: Foundation
- ✅ Phase 1: Fix Critical Bugs (Day 1)
- 🏗️ Phase 2: Infrastructure (Days 2-4)
- 💻 Phase 3: Start generators (Day 5)

### Week 2: Core Implementation
- 💻 Phase 3: Complete application logic (Days 1-4)
- 🔗 Phase 4: Wire pipeline (Day 5)

### Week 3: Quality & Documentation
- ✅ Phase 5: Add testing (Days 1-2)
- 📚 Phase 6: Documentation (Days 3-5)

### Week 4: Security & Polish
- 🔒 Phase 7: Security (Days 1-2)
- ✨ Phase 8: Polish (Days 3-5)

---

## Getting Help

### Stuck on a Task?

1. Review the specific task in ACTION_PLAN.md
2. Check AWS/dbt/Python documentation
3. Look for similar patterns in existing code
4. Create a draft PR and ask for feedback
5. Update ACTION_PLAN.md if you discover issues

### Found a Better Approach?

1. Document it in ACTION_PLAN.md
2. Create an issue to discuss
3. Update the plan before implementing
4. Share learnings in PR description

---

## Daily Workflow

**Morning**:
1. Review QUICK_CHECKLIST.md
2. Pick 1-3 tasks for today
3. Create/update GitHub issues

**During Work**:
4. Implement task
5. Test thoroughly
6. Update documentation
7. Commit with clear message

**End of Day**:
8. Update QUICK_CHECKLIST.md
9. Push work
10. Plan tomorrow's tasks

---

## Success Criteria for Each Phase

✅ **Phase Complete When**:
- All tasks checked off in QUICK_CHECKLIST.md
- All acceptance criteria met
- Tests passing
- Documentation updated
- Code reviewed (if team)
- PR merged

---

## Questions?

Check:
- ACTION_PLAN.md (comprehensive details)
- QUICK_CHECKLIST.md (quick reference)
- This guide (getting started)
- TODO.md (original notes)

**Good luck building! 🚀**
