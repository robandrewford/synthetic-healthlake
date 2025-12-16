# Release Checklist

This document defines the release process, versioning strategy, and pre-release validation steps for the synthetic-healthlake project.

## Version Strategy

This project follows [Semantic Versioning](https://semver.org/) (SemVer):

```text
MAJOR.MINOR.PATCH

Examples:
  1.0.0  - Initial stable release
  1.1.0  - New features, backward compatible
  1.1.1  - Bug fixes only
  2.0.0  - Breaking changes
```

### Version Increment Guidelines

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| Breaking API changes | MAJOR | Remove endpoint, change schema |
| New features (backward compatible) | MINOR | Add endpoint, new dbt model |
| Bug fixes | PATCH | Fix validation, correct typo |
| Documentation only | No bump | Update README, add guide |

---

## Release Types

### Production Release

Full release with version tag and changelog entry.

- **Tag format**: `v1.0.0`
- **Branch**: `main`
- **Artifacts**: Docker images, CDK templates

### Pre-release

Testing release for validation before production.

- **Tag format**: `v1.0.0-rc.1`, `v1.0.0-beta.1`
- **Branch**: `release/*` or `main`
- **Purpose**: Staging validation

### Hotfix

Emergency fix for production issues.

- **Tag format**: `v1.0.1`
- **Branch**: `hotfix/*` → `main`
- **Process**: Expedited review, immediate deploy

---

## Pre-Release Checklist

Complete ALL items before creating a release tag:

### Code Quality

- [ ] All tests passing: `uv run pytest`
- [ ] Linting clean: `uv run ruff check .`
- [ ] Type checking: `uv run mypy .`
- [ ] Pre-commit hooks pass: `uv run pre-commit run --all-files`

### dbt Validation

- [ ] Models compile: `dbt compile`
- [ ] Tests pass: `dbt test`
- [ ] Documentation generated: `dbt docs generate`

### Infrastructure

- [ ] CDK synth succeeds: `cd cdk && npm run synth`
- [ ] No security vulnerabilities: `npm audit`
- [ ] Python dependencies secure: `pip-audit`

### Documentation

- [ ] README up to date
- [ ] Changelog entry added
- [ ] API documentation current
- [ ] Breaking changes documented (if MAJOR bump)

### Validation

- [ ] Smoke test passes: `./scripts/smoke-test.sh`
- [ ] Sample dataset generates: `./scripts/generate-sample-dataset.sh --size small`
- [ ] Integration tests pass (if applicable)

---

## Release Process

### Step 1: Prepare Release Branch

```bash
# Create release branch
git checkout -b release/v1.0.0

# Update version in pyproject.toml
sed -i '' 's/version = ".*"/version = "1.0.0"/' pyproject.toml

# Update changelog
# Edit docs/development/changelog.md
```

### Step 2: Run Pre-Release Checklist

```bash
# Run all validations
uv run pre-commit run --all-files
uv run pytest
cd cdk && npm run synth && cd ..
./scripts/smoke-test.sh
```

### Step 3: Create Changelog Entry

Add entry to `docs/development/changelog.md`:

```markdown
## [1.0.0] - YYYY-MM-DD

### Added
- Feature A description
- Feature B description

### Changed
- Change description

### Fixed
- Bug fix description

### Removed
- Removed feature (BREAKING)

### Security
- Security fix description
```

### Step 4: Create Pull Request

```bash
# Push release branch
git push origin release/v1.0.0

# Create PR via GitHub CLI
gh pr create --title "Release v1.0.0" --body "Release checklist completed"
```

### Step 5: Merge and Tag

After PR approval:

```bash
# Merge to main
gh pr merge --squash

# Create tag
git checkout main
git pull
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Step 6: Create GitHub Release

```bash
# Create release with auto-generated notes
gh release create v1.0.0 \
  --title "v1.0.0" \
  --generate-notes
```

---

## Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

### Categories

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features to be removed
- **Removed**: Removed features (BREAKING)
- **Fixed**: Bug fixes
- **Security**: Security fixes

### Example Entry

```markdown
## [1.2.0] - 2024-01-15

### Added

- New `/api/observations` endpoint for lab results
- Performance benchmarking documentation
- Cleanup scripts for AWS resources

### Changed

- Improved synthetic data generation throughput (3x faster)
- Updated dbt to version 1.7

### Fixed

- Fixed gender distribution in synthetic data
- Resolved S3 bucket policy issue

### Security

- Updated dependencies to address CVE-2024-XXXX
```

---

## Hotfix Process

For urgent production fixes:

### Step 1: Create Hotfix Branch

```bash
git checkout main
git checkout -b hotfix/v1.0.1
```

### Step 2: Apply Fix

```bash
# Make minimal fix
# Update version in pyproject.toml to 1.0.1
# Add changelog entry
```

### Step 3: Fast-Track Review

```bash
# Create PR with hotfix label
gh pr create --title "Hotfix v1.0.1: Critical bug fix" \
  --label "hotfix" \
  --body "Emergency fix for [issue description]"
```

### Step 4: Deploy Immediately

After expedited review:

```bash
gh pr merge --squash
git checkout main && git pull
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1
gh release create v1.0.1 --title "v1.0.1 (Hotfix)"
```

---

## Automation

### GitHub Actions Workflow

The following workflows run automatically:

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `cdk-deploy.yml` | Push to main | CDK synth validation |
| `dbt-tests.yml` | PR | dbt compile and test |
| `synthetic-smoke.yml` | PR | Smoke test validation |

### Release Automation (Future)

Consider adding:

- [ ] Automatic version bump on merge
- [ ] Automatic changelog generation
- [ ] Docker image build on tag
- [ ] CDK deploy on release

---

## Related Documentation

- [Changelog](changelog.md)
- [Contributing Guide](contributing.md)
- [Coding Standards](coding-standards.md)
