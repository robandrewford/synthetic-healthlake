# Contributing to Synthetic HealthLake

Thank you for your interest in contributing to the FHIR-OMOP Synthetic Stack! This document provides guidelines and instructions for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for CDK infrastructure)
- AWS CLI configured (for deployment testing)
- Git

### Development Setup

1. **Clone the repository**

```bash
git clone https://github.com/robandrewford/synthetic-healthlake.git
cd synthetic-healthlake
```

2. **Install Python dependencies**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Install development dependencies (includes pre-commit)
uv sync --extra dev --extra test
```

3. **Install CDK dependencies**

```bash
cd cdk
npm install
cd ..
```

4. **Install pre-commit hooks**

```bash
pre-commit install
```

This will automatically run code quality checks before each commit.

## Development Workflow

### Pre-commit Hooks

We use pre-commit hooks to maintain code quality. The hooks will:

- **Lint Python code** with `ruff`
- **Format Python code** with `ruff format`
- **Type check** with `mypy` (health_platform and synthetic packages only)
- **Check YAML/JSON/TOML syntax**
- **Remove trailing whitespace**
- **Fix line endings**
- **Lint Markdown files**
- **Check for large files and private keys**
- **Format SQL** with `sqlfluff` (Snowflake dialect)

#### Running Pre-commit Manually

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run

# Run specific hook
pre-commit run ruff --all-files
```

#### Bypassing Pre-commit (Not Recommended)

```bash
git commit --no-verify -m "your message"
```

Only bypass pre-commit for emergency hotfixes. Clean up the code in a follow-up commit.

### Code Quality Standards

#### Python

- Follow PEP 8 style guide
- Use type hints for function signatures
- Maximum line length: 100 characters (enforced by ruff)
- Use descriptive variable names
- Add docstrings to all public functions/classes

```python
def process_patient_data(patient_id: str, include_observations: bool = False) -> dict[str, Any]:
    """
    Process patient data and return FHIR-compliant resource.

    Args:
        patient_id: Unique patient identifier
        include_observations: Whether to include related observations

    Returns:
        FHIR Patient resource dictionary

    Raises:
        ValueError: If patient_id is invalid
    """
    ...
```

#### TypeScript (CDK)

- Use TypeScript strict mode
- No `any` types without justification
- Document complex constructs with JSDoc comments
- Follow AWS CDK best practices

#### SQL (dbt)

- Lowercase keywords and table names
- Use 2-space indentation
- Always use `{{ ref() }}` for dbt models
- Add column-level documentation in schema YAML

### Testing

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_generators.py

# Run with coverage
pytest --cov=health_platform --cov=synthetic

# Run integration tests only
pytest tests/integration/
```

#### Writing Tests

- Place unit tests in `tests/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_patient_api_returns_404_for_missing_patient`
- Mock external services (S3, Snowflake, etc.) using `moto` or `pytest-mock`

Example:

```python
def test_patient_api_handles_missing_patient(mock_snowflake):
    """Verify 404 response when patient not found."""
    mock_snowflake.return_value = None

    response = get_patient("nonexistent-id", org_context)

    assert response["statusCode"] == 404
    assert "not found" in response["body"]
```

### Linting and Formatting

#### Python

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy health_platform/ synthetic/
```

#### TypeScript

```bash
cd cdk
npm run lint
npx tsc --noEmit
```

#### SQL

```bash
sqlfluff lint dbt/snowflake/models/ --dialect snowflake
sqlfluff fix dbt/snowflake/models/ --dialect snowflake
```

## Issue Tracking with Beads

This project uses [Beads](https://github.com/steveyegge/beads) for issue tracking. Issues are stored in `.beads/issues.jsonl` and sync with git.

### Working with Issues

```bash
# View all issues
bd list

# View ready (unblocked) issues
bd ready

# Create new issue
bd create "Add support for AllergyIntolerance resource" -t feature -p 1

# Update issue
bd update <issue-id> --status in_progress

# Close issue
bd close <issue-id> --reason "Implemented and tested"
```

### Commit Guidelines

Always commit `.beads/issues.jsonl` together with related code changes:

```bash
git add .beads/issues.jsonl health_platform/api/allergy.py
git commit -m "Add AllergyIntolerance API endpoint

Closes bd-xyz"
```

## Pull Request Process

1. **Create a feature branch**

```bash
git checkout -b feature/add-medication-api
```

2. **Make your changes**
   - Write tests for new functionality
   - Update documentation
   - Run pre-commit hooks

3. **Ensure all tests pass**

```bash
pytest
npm run test  # if you modified CDK
```

4. **Push and create PR**

```bash
git push origin feature/add-medication-api
```

5. **PR Requirements**
   - All CI checks must pass
   - At least one approving review
   - No merge conflicts
   - Pre-commit hooks pass

### PR Title Format

Use conventional commit format:

- `feat: Add MedicationRequest API endpoint`
- `fix: Handle null birthdate in patient search`
- `docs: Update API documentation for Observation resource`
- `test: Add integration tests for org isolation`
- `refactor: Simplify Snowflake connection pooling`
- `chore: Update dependencies`

## Project Structure

```
synthetic-healthlake/
├── health_platform/          # Lambda functions
│   ├── api/                 # FHIR API endpoints
│   ├── ingestion/           # Data ingestion lambdas
│   └── utils/               # Shared utilities
├── synthetic/               # Data generators
│   ├── generators/          # FHIR/OMOP generators
│   └── etl/                 # ETL logic
├── dbt/snowflake/          # dbt transformations
│   ├── models/staging/     # Staging models
│   └── models/marts/       # Analytics marts
├── cdk/                    # Infrastructure as code
├── tests/                  # Test suite
├── docs/                   # Documentation
└── scripts/                # Helper scripts
```

## Documentation

- Update relevant documentation when adding features
- Add inline comments for complex logic
- Update `docs/api/openapi.yaml` for API changes
- Add examples to docstrings

## Security

### Security-First Development

We take security seriously. All contributions must meet security standards:

- **Never commit real patient data** (only synthetic data allowed)
- **Never commit AWS credentials** or secrets
- Use AWS Secrets Manager for sensitive configuration
- Review [Security Documentation](docs/security/dependency-scanning.md)

### Automated Security Scanning

Security scans run automatically on:

- Every commit (pre-commit hooks)
- Every pull request (GitHub Actions)
- Weekly schedule (Mondays)
- Dependabot checks (automated PRs)

### Running Security Scans Locally

Use the convenience script to run all security checks:

```bash
./scripts/security-scan.sh
```

Or run individual scans:

```bash
# Check for secrets and private keys
pre-commit run detect-private-key --all-files

# Audit Python dependencies for vulnerabilities
uv pip install -e ".[security]"
pip-audit

# Python code security linting
bandit -r health_platform/ synthetic/

# Python security database check
safety check

# Audit Node.js dependencies
cd cdk && npm audit --audit-level=high

# Comprehensive filesystem scan
trivy fs --severity HIGH,CRITICAL .
```

### Security Requirements for PRs

All pull requests must:

1. ✅ Pass all pre-commit security hooks
2. ✅ Have no HIGH or CRITICAL vulnerabilities
3. ✅ Update dependencies if vulnerabilities found
4. ✅ Document any accepted security risks

### Responding to Security Issues

If you discover a security vulnerability:

1. **DO NOT** create a public issue
2. Email security concerns privately to maintainers
3. Include details: affected versions, impact, reproduction steps
4. Allow time for patch before public disclosure

### Dependency Updates

- Review Dependabot PRs promptly
- Test dependency updates in development first
- Security updates take priority over feature work
- Document breaking changes in CHANGELOG.md

See [Dependency Scanning Documentation](docs/security/dependency-scanning.md) for detailed information.

## Questions or Problems?

- Check existing documentation in `docs/`
- Review open issues: `bd list`
- Ask in pull request comments
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Synthetic HealthLake! 🎉
