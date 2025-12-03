# Contributing to FHIR-OMOP Synthetic Stack

## 1. How to Contribute
- Fork the repository.
- Create a feature branch.
- Submit a pull request with clear description and rationale.
- Ensure all CI workflows pass.

## 2. Code Standards
- CDK: TypeScript, strict mode, no unused variables.
- Python: PEP8, type hints encouraged.
- dbt: Use refs, seeds, and sources properly; include tests.

## 3. Testing Requirements
- `dbt test` must pass.
- Synthetic scripts must compile.
- CDK synth must succeed.

## 4. Pull Request Guidelines
- One logical change per PR.
- Include screenshots for docs changes.
- Tag maintainers for review.
